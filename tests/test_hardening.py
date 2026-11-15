"""Bounded work and actual HTTP parsing regressions, without opening a socket."""
import io
import json
from importlib.resources import files
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from eiv.fixtures import atom, rule, spec
from eiv.logic import ValidationError, analyze_spec
from eiv.permissions import parse_instruction, start_session, step_session
from eiv.planning import PlanningLimitError
from eiv.web import Handler, MAX_CONCURRENT_REQUESTS, REQUEST_TIMEOUT, WorkbenchServer


def case():
    return parse_instruction("You may send report to alex or bea once.",
                             dict(domain="messages", action="send", resource="report",
                                  recipient="alex", scope="once"), {})


class ResourceBoundTests(unittest.TestCase):
    def test_wide_expression_is_rejected_before_enumeration(self):
        model = spec(["Unit"], {"P": 0}, [], [], [],
                     {"or": [atom("P")] * 2048})
        with self.assertRaisesRegex(ValidationError, "expression nodes"):
            analyze_spec(model)

    def test_node_budget_is_shared_across_assertions(self):
        model = spec(["Unit"], {"P": 0}, [], [],
                     [{"or": [atom("P")] * 40}] * 63, atom("P"))
        with self.assertRaisesRegex(ValidationError, "expression nodes"):
            analyze_spec(model)

    def test_grounded_work_budget_returns_unknown_without_partial_claim(self):
        model = spec(["A", "B", "C", "D"], {"P": 1, "Q": 1, "R": 1}, [],
                     [rule(["?x", "?y", "?z"], atom("P", "?x"), atom("Q", "?y"))] * 20,
                     [], atom("R", "A"))
        result = analyze_spec(model)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["reason"], "evaluation_budget")
        self.assertEqual(result["assignments_examined"], 0)
        self.assertIsNone(result["theory_models"])
        self.assertIsNone(result["witness_query"])

    def test_explicit_work_limit_and_invalid_limits(self):
        model = spec(["Unit"], {"P": 0}, [], [], [], atom("P"))
        self.assertEqual(analyze_spec(model, max_evaluations=1)["status"], "unknown")
        self.assertEqual(analyze_spec(model, max_evaluations=2)["status"], "underdetermined")
        for limit in (True, 0, -1, 1.5, "10"):
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                analyze_spec(model, max_evaluations=limit)

    def test_unbounded_identifiers_are_rejected(self):
        name = "P" * 65
        model = spec(["Unit"], {name: 0}, [], [], [], atom(name))
        with self.assertRaisesRegex(ValidationError, "64 characters"):
            analyze_spec(model)


class ReplayBoundaryTests(unittest.TestCase):
    def test_optimal_session_resolves_counterexample_and_enforces_budget(self):
        example = json.loads(files("eiv").joinpath("assets/selection-example.json").read_text())
        state = start_session(example, max_questions=1, question_strategy="optimal")
        self.assertEqual(state["result"]["suggested_question"]["id"], "isolate")
        last = step_session(state, {"question": "isolate", "answer": "last"})
        self.assertEqual(last["result"]["decision"], "deny")
        self.assertEqual(last["question_strategy"], "optimal")
        rest = step_session(state, {"question": "isolate", "answer": "rest"})
        self.assertEqual(rest["result"]["decision"], "abstain")
        self.assertEqual(rest["result"]["reason"], "question_budget_exhausted")
        self.assertEqual(start_session(example, 0, "optimal")["result"]["reason"], "question_budget_exhausted")

    def test_planning_limit_fails_closed_with_no_question(self):
        with patch("eiv.planning.select_question", side_effect=PlanningLimitError("bounded search")):
            result = start_session(case(), question_strategy="optimal")["result"]
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["reason"], "clarification_planning_limit")
        self.assertIsNone(result["suggested_question"])
        self.assertEqual(result["trace"][-1]["decision"], "abstain")

    def test_client_cache_is_not_copied_or_trusted(self):
        class PoisonedCache:
            def __deepcopy__(self, memo):
                raise AssertionError("client result must not be copied")
        state = start_session(case())
        state["result"] = PoisonedCache()
        result = step_session(state, {"question": "interpretation", "answer": "c2"})
        self.assertEqual(result["result"]["decision"], "deny")

    def test_invalid_sessions_raise_validation_errors(self):
        for field, value in (("answers", None), ("answers", {}),
                             ("answers", [{"question": [], "answer": "c1"}]),
                             ("max_questions", True), ("max_questions", "2"),
                             ("case", [])):
            state = start_session(case())
            state[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                step_session(state, {"question": "interpretation", "answer": "c2"})

    def test_replay_budget_and_strategy_remain_explicit(self):
        state = start_session(case(), max_questions=1, question_strategy="first")
        final = step_session(state, {"question": "interpretation", "answer": "c2"})
        self.assertEqual(final["question_strategy"], "first")
        with self.assertRaisesRegex(ValidationError, "budget"):
            step_session(final, {"question": "interpretation", "answer": "c1"})
        self.assertNotIn("question_strategy", start_session(case()))


class MemorySocket:
    """Use BaseHTTPRequestHandler's real request parsing over byte streams."""
    def __init__(self, raw):
        self.input = io.BytesIO(raw)
        self.output = io.BytesIO()
        self.timeout = None

    def makefile(self, *_args, **_kwargs):
        return self.input

    def sendall(self, body):
        self.output.write(body)

    def settimeout(self, value):
        self.timeout = value


class HTTPParsingBoundaryTests(unittest.TestCase):
    def send(self, headers=(), body=b"{}", method="POST", path="/api/analyze", default_length=True):
        lines = [f"{method} {path} HTTP/1.1", "Host: 127.0.0.1:8765",
                 "Content-Type: application/json"]
        if default_length:
            lines.append(f"Content-Length: {len(body)}")
        raw = ("\r\n".join(lines + list(headers)) + "\r\n\r\n").encode() + body
        sock = MemorySocket(raw)
        Handler(sock, ("127.0.0.1", 34567), SimpleNamespace(server_port=8765))
        self.assertEqual(sock.timeout, REQUEST_TIMEOUT)
        head, payload = sock.output.getvalue().split(b"\r\n\r\n", 1)
        status = int(head.split(b" ")[1])
        return status, head, payload

    def test_duplicate_security_headers_and_cross_site_fetch_are_rejected(self):
        for headers in (("Host: evil.example",), ("Host: localhost:8765",),
                        ("Origin: http://127.0.0.1:8765", "Origin: http://127.0.0.1:8765"),
                        ("Origin:",), ("Sec-Fetch-Site: cross-site",)):
            with self.subTest(headers=headers):
                self.assertEqual(self.send(headers)[0], 403)

    def test_ambiguous_framing_is_rejected(self):
        for headers in (("Content-Length: 2",), ("Content-Length: 999",),
                        ("Transfer-Encoding: chunked",), ("Transfer-Encoding:",)):
            with self.subTest(headers=headers):
                self.assertEqual(self.send(headers)[0], 400)
        for length in ("+2", "-2", "1, 2", "99999999999", "two"):
            with self.subTest(length=length):
                self.assertEqual(self.send((f"Content-Length: {length}",), default_length=False)[0], 400)
        self.assertEqual(self.send(default_length=False)[0], 400)

    def test_duplicate_content_types_and_unknown_routes(self):
        self.assertEqual(self.send(("Content-Type: text/plain",))[0], 415)
        self.assertEqual(self.send(path="/api/missing")[0], 404)

    def test_security_headers_and_real_engine_round_trip(self):
        status, head, payload = self.send(method="GET", path="/api/health", body=b"")
        self.assertEqual(status, 200)
        for header in (b"Cache-Control: no-store", b"X-Content-Type-Options: nosniff",
                       b"Referrer-Policy: no-referrer", b"X-Frame-Options: DENY",
                       b"Cross-Origin-Resource-Policy: same-origin"):
            self.assertIn(header, head)
        self.assertNotIn(b"Python/", head)
        body = json.dumps({"case": case(), "max_questions": 1}).encode()
        status, _, payload = self.send(path="/api/structured", body=body)
        self.assertEqual(status, 200)
        state = json.loads(payload)
        body = json.dumps({"session": state, "answer": {"question": "interpretation", "answer": "c2"}}).encode()
        status, _, payload = self.send(path="/api/step", body=body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["result"]["decision"], "deny")

    def test_packaged_examples_and_strategy_api(self):
        for path in ("/", "/api/dimension-example", "/api/selection-example"):
            status, _, payload = self.send(method="GET", path=path, body=b"")
            self.assertEqual(status, 200)
            self.assertTrue(payload)
        body = json.dumps({"case": case(), "max_questions": 1, "question_strategy": "optimal"}).encode()
        status, _, payload = self.send(path="/api/structured", body=body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["question_strategy"], "optimal")

    def test_server_connection_cap_releases_slots_even_on_failure(self):
        # No real listening socket is needed to exercise admission/release.
        import threading
        server = WorkbenchServer.__new__(WorkbenchServer)
        server._slots = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
        server.shutdown_request = Mock()
        with patch("http.server.ThreadingHTTPServer.process_request") as launch:
            for _ in range(MAX_CONCURRENT_REQUESTS):
                server.process_request("socket", "client")
            server.process_request("overflow", "client")
            self.assertEqual(launch.call_count, MAX_CONCURRENT_REQUESTS)
            server.shutdown_request.assert_called_once_with("overflow")
            with patch("http.server.ThreadingHTTPServer.process_request_thread", side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    server.process_request_thread("socket", "client")
            server.process_request("replacement", "client")
            self.assertEqual(launch.call_count, MAX_CONCURRENT_REQUESTS + 1)


if __name__ == "__main__":
    unittest.main()
