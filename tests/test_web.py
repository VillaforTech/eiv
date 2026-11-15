"""Exercise the HTTP boundary and actual interactive permission path."""
from copy import deepcopy
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from eiv.web import Handler, process
from eiv.logic import ValidationError


def packet():
    return {"instruction": "You may send report to alex or bea once.",
            "request": {"domain": "messages", "action": "send", "resource": "report", "recipient": "alex", "scope": "once"},
            "facts": {}, "max_questions": 2}


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def send(self, method, path, value=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = raw if raw is not None else json.dumps(value) if value is not None else None
        try:
            conn.request(method, path, body, {"Content-Type": "application/json", **(headers or {})})
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_http_question_then_each_terminal_outcome(self):
        for answer, expected in [("c1", "allow"), ("c2", "deny"), ("other", "abstain"), ("unsure", "abstain")]:
            status, body = self.send("POST", "/api/analyze", packet())
            self.assertEqual(status, 200)
            session = json.loads(body)
            self.assertEqual(session["result"]["decision"], "ask")
            status, body = self.send("POST", "/api/step", {"session": session, "answer": {"question": "interpretation", "answer": answer}})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["result"]["decision"], expected)

    def test_cross_origin_and_rebound_host_rejected(self):
        for headers in [{"Origin": "https://example.com"}, {"Host": "example.com"}, {"Origin": "null"}]:
            self.assertEqual(self.send("POST", "/api/analyze", packet(), headers)[0], 403)

    def test_malformed_duplicate_and_oversized_bodies(self):
        for raw in ["{", '{"case":1,"case":2}', "[]"]:
            self.assertEqual(self.send("POST", "/api/structured", raw=raw)[0], 400)
        # Preserve/reject duplicate facts across browser transport rather than
        # silently accepting the final value as an authorization fact.
        duplicate_facts = json.dumps(packet()).replace('"facts": {}', '"facts": {"approved": false, "approved": true}')
        status, body = self.send("POST", "/api/analyze", raw=duplicate_facts)
        self.assertEqual(status, 400)
        self.assertIn(b'duplicate JSON key: approved', body)
        self.assertEqual(self.send("POST", "/api/analyze", raw=" " * 100001)[0], 413)
        self.assertEqual(self.send("POST", "/api/analyze", packet(), {"Content-Type": "text/plain"})[0], 415)
        session = process("/api/analyze", packet())
        session["answers"] = {}
        self.assertEqual(self.send("POST", "/api/step", {"session": session, "answer": {}})[0], 400)

    def test_no_arbitrary_file_routes(self):
        for route in ["/../README.md", "/.git/config", "/api/unknown"]:
            self.assertEqual(self.send("GET", route)[0], 404)
        status, body = self.send("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["model_calls"])

    def test_dimension_example_excludes_private_oracle_and_selects_target(self):
        status, body = self.send("GET", "/api/dimension-example")
        self.assertEqual(status, 200)
        case = json.loads(body)
        self.assertNotIn("oracle", case)
        self.assertNotIn("gold_decision", case)
        self.assertEqual(case["questions"][0]["id"], "d1")
        session = process("/api/structured", {"case": case, "max_questions": 1})
        self.assertEqual(session["result"]["suggested_question"]["id"], "d0")
        self.assertEqual(session["result"]["questions_used"], 0)

    def test_unknown_semantics_abstain_and_tampering_rejected(self):
        p = packet()
        p["instruction"] = "Do whatever is useful."
        self.assertEqual(process("/api/analyze", p)["result"]["decision"], "abstain")
        session = process("/api/analyze", packet())
        changed = deepcopy(session)
        changed["case"]["request"]["scope"] = "session"
        with self.assertRaisesRegex(ValidationError, "digest mismatch"):
            process("/api/step", {"session": changed, "answer": {"question": "interpretation", "answer": "c1"}})
        # A client result is ignored, not trusted as a permission token.
        changed = deepcopy(session)
        changed["result"]["decision"] = "allow"
        self.assertEqual(process("/api/step", {"session": changed, "answer": {"question": "interpretation", "answer": "c2"}})["result"]["decision"], "deny")

    def test_selector_counterexample_asks_but_does_not_resolve_at_budget_one(self):
        status, body = self.send("GET", "/api/selection-example")
        self.assertEqual(status, 200)
        case = json.loads(body)
        session = process("/api/structured", {"case": case, "max_questions": 1})
        question = session["result"]["suggested_question"]
        self.assertEqual(question["id"], "balanced")
        self.assertNotIn("gold_decision", case)
        self.assertNotIn("latent", case)
        for answer in question["answers"]:
            result = process("/api/step", {"session": session, "answer": {"question": question["id"], "answer": answer["id"]}})
            self.assertEqual(result["result"]["decision"], "abstain")
            self.assertEqual(result["result"]["questions_used"], 1)


if __name__ == "__main__":
    unittest.main()
