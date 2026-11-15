"""Local research workbench: python -m eiv.web --port 8765.

Uses the real permission engine. It never executes an action or calls a model.
The client-supplied session is a replay record, not a signed permission token.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .logic import ValidationError
from .permissions import (
    _unique_json_object, load_structured_case, parse_instruction,
    start_session, step_session,
)

ROOT = Path(__file__).resolve().parents[1]
BODY_LIMIT = 100_000


def process(path, payload):
    if not isinstance(payload, dict):
        raise ValidationError("request must be a JSON object")
    if path == "/api/analyze":
        if set(payload) != {"instruction", "request", "facts", "max_questions"}:
            raise ValidationError("analyze requires instruction, request, facts and max_questions")
        case = parse_instruction(payload["instruction"], payload["request"], payload["facts"])
        return start_session(case, payload["max_questions"])
    if path == "/api/structured":
        if set(payload) != {"case", "max_questions"}:
            raise ValidationError("structured requires case and max_questions")
        return start_session(load_structured_case(payload["case"]), payload["max_questions"])
    if path == "/api/step":
        if set(payload) != {"session", "answer"}:
            raise ValidationError("step requires session and answer")
        state = payload["session"]
        if not isinstance(state, dict) or not isinstance(state.get("answers"), list):
            raise ValidationError("session answers must be a list")
        return step_session(payload["session"], payload["answer"])
    raise ValidationError("unknown API route")


class Handler(BaseHTTPRequestHandler):
    server_version = "EIVResearch/0.3"

    def log_message(self, *_):
        pass  # No instructions or user content in console logs.

    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in hosts:
            self.reply(403, {"error": "loopback Host required"})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in hosts}:
            self.reply(403, {"error": "cross-origin access is disabled"})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        if self.path == "/":
            self.reply(200, (ROOT / "deliverables/workbench.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self.reply(200, {"status": "ok", "simulated": True, "model_calls": False})
        elif self.path == "/api/dimension-example":
            with (ROOT / "benchmark/v3/cases.jsonl").open() as stream:
                for line in stream:
                    row = json.loads(line)
                    if row["family"] == "recipient" and row["condition"] == "complete" and row["question_order"] == [1, 2, 0]:
                        self.reply(200, row["public"])
                        return
            self.reply(404, {"error": "dimension example unavailable"})
        elif self.path == "/api/selection-example":
            case = load_structured_case((ROOT / "results/selection-audit-final-20261023/counterexample-case.json").read_text())
            self.reply(200, case)
        elif self.path == "/favicon.ico":
            self.reply(204, b"")
        else:
            self.reply(404, {"error": "route not found"})

    def do_POST(self):
        if not self.local_request():
            return
        if self.headers.get_content_type() != "application/json":
            self.reply(415, {"error": "application/json required"})
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise ValidationError("chunked bodies are unsupported")
            size = int(self.headers.get("Content-Length", "0"))
            self.connection.settimeout(5)
            if not 0 < size <= BODY_LIMIT:
                # Drain a bounded prefix before closing. In particular a body
                # one byte over the limit should receive 413, not race a TCP
                # reset while the client is still writing its first chunk.
                if size > BODY_LIMIT:
                    self.rfile.read(min(size, BODY_LIMIT + 1))
                self.reply(413, {"error": "body must contain 1-100000 bytes"})
                return
            body = self.rfile.read(size)
            if len(body) != size:
                raise ValidationError("incomplete body")
            payload = json.loads(body, object_pairs_hook=_unique_json_object)
            self.reply(200, process(self.path, payload))
        except (ValidationError, ValueError, TypeError, KeyError, RecursionError, UnicodeError) as error:
            self.reply(400, {"error": str(error)[:500]})
        except TimeoutError:
            self.reply(408, {"error": "request body timed out"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be 0-65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"EIV simulated workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
