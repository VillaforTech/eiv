"""Command-line entry point: python -m eiv."""

import argparse
import json
from pathlib import Path

from .benchmark import run_benchmark
from .fixtures import build_suite
from .logic import ValidationError, analyze_spec
from .workflow import analyze_case
from .permissions import parse_instruction, analyze_request, load_structured_case, _unique_json_object


def _print(value):
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Bounded EIV simulated authorization and legacy logical fixtures")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="evaluate a case JSON or a single spec JSON")
    analyze.add_argument("path", type=Path)
    clarify = commands.add_parser("clarify", help="apply one answer to a predeclared question")
    clarify.add_argument("path", type=Path)
    clarify.add_argument("question")
    clarify.add_argument("answer")
    demo = commands.add_parser("demo", help="summarize all manually formalized examples")
    demo.add_argument("--full", action="store_true", help="include complete models")
    benchmark = commands.add_parser("benchmark", help="run the deterministic fixture benchmark")
    benchmark.add_argument("--output", type=Path)
    fixtures = commands.add_parser("write-fixtures", help="write canonical case JSON files")
    fixtures.add_argument("--dir", type=Path, default=Path("fixtures"))
    auth = commands.add_parser("authorize", help="simulate a validated permission case")
    auth.add_argument("path", type=Path)
    auth.add_argument("--answer", action="append", default=[], help="question_id=answer_id; other/unsure allowed")
    nl = commands.add_parser("interpret", help="parse documented controlled English and simulate")
    nl.add_argument("instruction")
    nl.add_argument("--domain", choices=["files", "messages"], required=True)
    nl.add_argument("--action", required=True)
    nl.add_argument("--resource", required=True)
    nl.add_argument("--recipient")
    nl.add_argument("--scope", choices=["once", "session"], default="once")
    nl.add_argument("--facts", default="{}", help="JSON booleans; omitted facts are unknown")
    args = parser.parse_args()
    try:
        if args.command == "authorize":
            case = load_structured_case(args.path.read_text(encoding="utf-8"))
            answers = []
            for item in args.answer:
                if "=" not in item:
                    raise ValidationError("answer requires question_id=answer_id")
                question, answer = item.split("=", 1)
                answers.append({"question": question, "answer": answer})
            _print(analyze_request(case, answers=answers))
        elif args.command == "interpret":
            request = {key: getattr(args, key) for key in ("domain", "action", "resource", "recipient", "scope")}
            case = parse_instruction(args.instruction, request, json.loads(args.facts, object_pairs_hook=_unique_json_object))
            _print({"generated_case": case, "result": analyze_request(case)})
        elif args.command in ("analyze", "clarify"):
            data = json.loads(args.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
            if not isinstance(data, dict):
                raise ValidationError("input file must contain a JSON object")
            if args.command == "clarify":
                result = analyze_case(data, {"question": args.question, "answer": args.answer})
            elif "candidates" in data:
                result = analyze_case(data)
            else:
                result = analyze_spec(data)
            _print(result)
        elif args.command == "demo":
            rows = []
            for item in build_suite():
                result = analyze_case(item["case"])
                rows.append({"id": item["id"], "split": item["split"],
                             "action": result["action"], "answer": result["answer"],
                             "candidate_statuses": {c["id"]: c["result"]["status"] for c in result["candidates"]},
                             "suggested_question": result["suggested_question"]})
            _print([analyze_case(item["case"]) for item in build_suite()] if args.full else rows)
        elif args.command == "benchmark":
            result = run_benchmark()
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _print(result)
        else:
            args.dir.mkdir(parents=True, exist_ok=True)
            paths = []
            for item in build_suite():
                path = args.dir / (item["id"] + ".json")
                path.write_text(json.dumps(item["case"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
                paths.append(str(path))
            _print({"written": paths})
    except (ValidationError, OSError, json.JSONDecodeError, RecursionError, UnicodeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
