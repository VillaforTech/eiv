# Usage and API

Use the repository root for source commands. `python3 -m eiv --help` lists the
CLI. After `pip install .`, `eiv` and `eiv-workbench` are equivalent entry points.
The installed wheel includes the workbench and its examples. Experiments need
the checkout's versioned data.

## Controlled English

```text
You may read report once.
You may send report to alex or bea once.
You may read report for this session if approved is true.
You must not delete report once.
```

Combine clauses with a semicolon. Identifiers are bounded ASCII names. The
published grammar is deliberately narrow: arbitrary prose is not an LLM task
and returns unknown semantics. Do not infer general language understanding from
these examples. Use the [schema](../schemas/permission-case.schema.json) for
explicit structured cases.

## Python

```python
from eiv.permissions import parse_instruction, start_session, step_session

request = dict(domain="messages", action="send", resource="report",
               recipient="alex", scope="once")
case = parse_instruction("You may send report to alex or bea once.", request, {})
session = start_session(case, max_questions=1, question_strategy="optimal")
question = session["result"]["suggested_question"]
if question:
    # Choose only an answer the user actually supplied; this is an example.
    session = step_session(session, {"question": question["id"], "answer": "unsure"})
assert session["result"]["decision"] == "abstain"
```

`targeted` remains the default historical greedy heuristic. `first` chooses the
first relevant partition. `optimal` uses bounded exact search. Valid budgets are
0–8. Outcomes are `allow`, `deny`, `ask`, `abstain`; they never execute anything.

## Local HTTP API

Start `python3 -m eiv.web --port 8765`. Same-origin requests only; JSON bodies
must be 1–100,000 bytes with one Content-Length and no duplicate JSON keys.

| Method and route | Input | Output |
|---|---|---|
| `GET /` | — | Packaged interactive workbench |
| `GET /api/health` | — | Simulator health; no model calls |
| `GET /api/dimension-example` | — | Public eight-candidate case without oracle |
| `GET /api/selection-example` | — | Greedy selector counterexample |
| `POST /api/analyze` | `instruction`, `request`, `facts`, `max_questions`; optional `question_strategy` | Initial replay session |
| `POST /api/structured` | `case`, `max_questions`; optional `question_strategy` | Validated initial session |
| `POST /api/step` | `session`, `answer: {question, answer}` | Recomputed next session |

Client sessions contain the case, its digest, answer history, question budget
and result; nondefault strategies are also recorded. The server recomputes from
validated case/history and never trusts the supplied result. Retain the whole
session when exporting evidence. Error responses have an `error` string.

Host and Origin checks, fixed routes, input bounds and timeouts reduce local
attack surface. They do not make this standard-library server suitable for
Internet exposure. See [SECURITY.md](../SECURITY.md).

## Portfolio draft

Open `portfolio/index.html` directly. It has no server, dependencies, telemetry
or model calls. Its interactive explanation is an educational simulation; use
the workbench for actual Python evaluation. The copy and integration notes are
in `portfolio/website-copy.md`. Publication is a separate hosting operation.
