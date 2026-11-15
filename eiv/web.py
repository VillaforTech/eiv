"""Local research workbench: python -m eiv.web --port 8765.

Uses the real permission engine. It never executes an action or calls a model.
The client-supplied session is a replay record, not a signed permission token.
"""
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import threading

from .logic import ValidationError
from .permissions import (
    _unique_json_object, load_structured_case, parse_instruction,
    start_session, step_session,
)

BODY_LIMIT = 100_000
REQUEST_TIMEOUT = 5
MAX_CONCURRENT_REQUESTS = 16


class WorkbenchServer(ThreadingHTTPServer):
    """Bound simultaneous local connections; this is not a production server."""
    daemon_threads = True
    request_queue_size = MAX_CONCURRENT_REQUESTS

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def process(path, payload):
    if not isinstance(payload, dict):
        raise ValidationError("request must be a JSON object")
    if path == "/api/analyze":
        if set(payload) - {"question_strategy"} != {"instruction", "request", "facts", "max_questions"}:
            raise ValidationError("analyze requires instruction, request, facts and max_questions")
        case = parse_instruction(payload["instruction"], payload["request"], payload["facts"])
        return start_session(case, payload["max_questions"], payload.get("question_strategy", "targeted"))
    if path == "/api/structured":
        if set(payload) - {"question_strategy"} != {"case", "max_questions"}:
            raise ValidationError("structured requires case and max_questions")
        return start_session(load_structured_case(payload["case"]), payload["max_questions"], payload.get("question_strategy", "targeted"))
    if path == "/api/step":
        if set(payload) != {"session", "answer"}:
            raise ValidationError("step requires session and answer")
        state = payload["session"]
        if not isinstance(state, dict) or not isinstance(state.get("answers"), list):
            raise ValidationError("session answers must be a list")
        return step_session(payload["session"], payload["answer"])
    raise ValidationError("unknown API route")


class Handler(BaseHTTPRequestHandler):
    server_version = "EIVWorkbench"
    sys_version = ""

    def setup(self):
        # Covers request headers as well as bodies. Combined with the server's
        # connection cap, idle clients cannot create unlimited waiting threads.
        self.request.settimeout(REQUEST_TIMEOUT)
        super().setup()

    def log_message(self, *_):
        pass  # No instructions or user content in console logs.

    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if len(self.headers.get_all("Host", [])) != 1 or self.headers.get("Host") not in hosts:
            self.reply(403, {"error": "loopback Host required"})
            return False
        origin = self.headers.get("Origin")
        if (len(self.headers.get_all("Origin", [])) > 1
                or origin is not None and origin not in {f"http://{host}" for host in hosts}
                or self.headers.get("Sec-Fetch-Site") == "cross-site"):
            self.reply(403, {"error": "cross-origin access is disabled"})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        if self.path == "/":
            self.reply(200, files("eiv").joinpath("assets/workbench.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self.reply(200, {"status": "ok", "simulated": True, "model_calls": False})
        elif self.path == "/api/dimension-example":
            case = load_structured_case(files("eiv").joinpath("assets/dimension-example.json").read_text(encoding="utf-8"))
            self.reply(200, case)
        elif self.path == "/api/selection-example":
            case = load_structured_case(files("eiv").joinpath("assets/selection-example.json").read_text(encoding="utf-8"))
            self.reply(200, case)
        elif self.path == "/favicon.ico":
            self.reply(204, b"")
        else:
            self.reply(404, {"error": "route not found"})

    def do_POST(self):
        if not self.local_request():
            return
        if self.path not in {"/api/analyze", "/api/structured", "/api/step"}:
            self.reply(404, {"error": "route not found"})
            return
        if len(self.headers.get_all("Content-Type", [])) != 1 or self.headers.get_content_type() != "application/json":
            self.reply(415, {"error": "application/json required"})
            return
        try:
            if self.headers.get_all("Transfer-Encoding"):
                raise ValidationError("chunked bodies are unsupported")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
                raise ValidationError("one decimal Content-Length is required")
            size = int(lengths[0])
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
    server = WorkbenchServer(("127.0.0.1", args.port), Handler)
    print(f"EIV simulated workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
