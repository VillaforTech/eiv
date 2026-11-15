"""Post-hoc evaluation of the current exact planner on already exposed inputs.

This is an engineering extension, not a new held-out validation. The driver
alone reads latent dimensions and supplies one answer to the question selected
by the real current core. Historical datasets, manifests and outcomes are never
rewritten. No model, network inference or actual file/message action is used.
"""

import argparse
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path
import time

from eiv.permissions import analyze_request, evaluate_candidate
from eiv.planning import plan_questions
from eiv_experiment.dimensions import dimension_answer
from eiv_experiment.selection_audit import (
    counterexample_case, independent_metrics, operation_membership,
)


ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ("targeted", "first", "optimal")
BUDGETS = (0, 1, 2, 3)
SCHEMA = "eiv-planner-4.0"
SOURCE_PATHS = ("eiv/planning.py", "eiv/permissions.py", "eiv/logic.py",
                "eiv_experiment/planner.py", "eiv_experiment/dimensions.py",
                "eiv_experiment/selection_audit.py")
INPUT_PATHS = ("benchmark/v3/cases.jsonl", "benchmark/v3/manifest.json")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _run_public(public, strategy, budget, answerer):
    """The core receives public JSON and the observed answer history only."""
    history = []
    result = analyze_request(public, max_questions=budget, question_strategy=strategy)
    while result["decision"] == "ask":
        _require(len(history) < budget, "core requested a question beyond its budget")
        question = result["suggested_question"]
        answer = answerer(question)
        history.append({"question": question["id"], "answer": answer})
        result = analyze_request(public, history, max_questions=budget,
                                 question_strategy=strategy)
    _require(result["decision"] in {"allow", "deny", "abstain"}, "invalid terminal decision")
    return result, history


def run_case(case, strategy, budget):
    result, history = _run_public(
        case["public"], strategy, budget,
        lambda question: dimension_answer(question, case["oracle"]))
    gold = case["gold_decision"]
    _require(gold in {"allow", "deny"}, "unexpected benchmark decision")
    # Label-dependent diagnostics are computed only after the policy returns.
    return {
        "case_id": case["case_id"], "family": case["family"],
        "condition": case["condition"], "arm": strategy, "budget": budget,
        "gold_decision": gold, "decision": result["decision"], "reason": result["reason"],
        "questions": result["questions_used"], "answers": history,
        "correct_resolved": result["decision"] == gold,
        "false_authorization": result["decision"] == "allow" and gold == "deny",
        "false_denial": result["decision"] == "deny" and gold == "allow",
        "initial_candidate_coverage": case["initial_candidate_coverage"],
        "retained_candidate_coverage": case["oracle"]["latent_candidate_id"] in result["active_candidate_ids"],
        "active_candidate_ids": result["active_candidate_ids"],
        "candidate_decisions": {row["id"]: row["decision"] for row in result["candidates"]},
        "trace": result["trace"],
    }


def _by_budget(rows):
    return {str(budget): {
        strategy: independent_metrics(
            [row for row in rows if row["budget"] == budget and row["arm"] == strategy],
            "gold_decision")
        for strategy in STRATEGIES} for budget in BUDGETS}


def summarize(rows):
    keys = [(r["case_id"], r["arm"], r["budget"]) for r in rows]
    cases = {r["case_id"] for r in rows}
    _require(len(keys) == len(set(keys)), "duplicate case/strategy/budget outcome")
    _require(set(keys) == set(itertools.product(cases, STRATEGIES, BUDGETS)),
             "incomplete case/strategy/budget outcomes")
    return {
        "schema": SCHEMA, "kind": "post_hoc_current_core_engineering_extension",
        "case_count": len(cases), "records": len(rows),
        "strategies": list(STRATEGIES), "budgets": list(BUDGETS),
        "human_labels_reviewed": False, "model_calls": 0,
        "external_monetary_cost_usd": 0,
        "independence": "Repeated cases, question orders and budgets are correlated; no population inference.",
        "exposure": "All inputs and the selection counterexample were inspected before this extension.",
        "metrics_by_budget": _by_budget(rows),
        "by_condition": {condition: _by_budget([r for r in rows if r["condition"] == condition])
                         for condition in sorted({r["condition"] for r in rows})},
        "by_family": {family: _by_budget([r for r in rows if r["family"] == family])
                      for family in sorted({r["family"] for r in rows})},
    }


def evaluate_counterexample():
    public = counterexample_case()
    # Independent concrete-operation denotation supplies the driver labels.
    decisions = {c["id"]: operation_membership(public["request"], public["facts"], c)
                 for c in public["candidates"]}
    rows = []
    for budget, strategy, intended in itertools.product(BUDGETS, STRATEGIES, decisions):
        result, history = _run_public(public, strategy, budget, lambda question:
            next(a["id"] for a in question["answers"] if intended in a["retain"]))
        _require(all(row["decision"] == decisions[row["id"]] for row in result["candidates"]),
                 "core candidate decision differs from independent denotation")
        _require(result["decision"] in {"abstain", decisions[intended]},
                 "incorrect resolved decision with truthful answers and complete coverage")
        rows.append({"case_id": "counterexample-" + intended, "latent_candidate": intended,
                     "arm": strategy, "budget": budget, "gold_decision": decisions[intended],
                     "decision": result["decision"], "reason": result["reason"],
                     "questions": result["questions_used"], "answers": history,
                     "active_candidate_ids": result["active_candidate_ids"], "trace": result["trace"]})
    checks = [evaluate_candidate(public["request"], public["facts"], c)
              for c in public["candidates"]]
    diagnostics = {str(budget): plan_questions(public["questions"], checks, list(decisions), budget)
                   for budget in BUDGETS}
    for plan in diagnostics.values():
        plan["suggested_question"] = plan["suggested_question"]["id"] if plan["suggested_question"] else None
    metrics = _by_budget(rows)
    for budget in BUDGETS:
        actual = metrics[str(budget)]["optimal"]
        expected = diagnostics[str(budget)]
        _require(actual["correct_resolved_n"] == expected["resolved_candidates"]
                 and actual["questions_total"] == expected["total_questions"],
                 "integrated core differs from exact planner objective")
    nonselecting = []
    for strategy, budget, answer in itertools.product(STRATEGIES, (1, 2, 3), ("other", "unsure")):
        result, history = _run_public(public, strategy, budget, lambda _question: answer)
        _require(result["decision"] == "abstain" and len(history) == 1,
                 "nonselecting answer did not terminate with abstention")
        nonselecting.append({"arm": strategy, "budget": budget, "answer": answer,
                             "decision": result["decision"], "questions": result["questions_used"]})
    return public, rows, {
        "kind": "previously_exposed_counterexample_post_hoc_extension",
        "records": len(rows), "candidate_count": len(decisions),
        "metrics_by_budget": metrics, "exact_objective_by_budget": diagnostics,
        "nonselecting_answer_checks": nonselecting,
        "interpretation": "Exact finite equal-candidate accounting; no prior over human intention or coverage guarantee.",
    }


def markdown(summary, counter):
    lines = ["# Exact clarification planning: post-hoc engineering extension", "",
             "This evaluates the current core on already inspected v3 cases and the known greedy-selection counterexample. It is not held-out validation, a human study, or evidence of general LLM safety. Historical manifests and outcomes remain unchanged.", "",
             f"The driver evaluates {summary['case_count']:,} supplied cases across three policies and four budgets, producing {summary['records']:,} deterministic outcomes. Only the driver reads latent intent. The core receives public candidates, finite consequences and the answer to its selected question. Repeated cases, orders and budgets are correlated.", "",
             "## Declared objective", "",
             "The optional `optimal` policy uses bounded dynamic programming to maximize the count of supplied candidate hypotheses reaching unanimous allow/deny within the budget, then minimize the total questions across all hypotheses (including unresolved branches), then preserve input question order. Each candidate counts once; these are not probabilities of human intent. A branch can stop and abstain when asking cannot improve resolution. Search-limit exhaustion abstains; it never returns an approximate authorization.", "",
             "## Complete coverage at one question", "",
             "| Policy | Correct / cases | False allow / latent deny | False deny / latent allow | Abstain / cases | Questions |",
             "|---|---:|---:|---:|---:|---:|"]
    for strategy in STRATEGIES:
        m = summary["by_condition"]["complete"]["1"][strategy]
        lines.append(f"| {strategy} | {m['correct_resolved_n']}/{m['n']} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['abstention_n']}/{m['n']} | {m['questions_total']} |")
    lines.extend(["", "V3 was constructed with a question that perfectly separates permitting and denying candidates. Matching the targeted policy here is expected; it does not establish general superiority.", "",
                  "## Known eight-candidate counterexample", "",
                  "| Budget | Policy | Correct / 8 | Abstain / 8 | False allow | False deny | Total questions |",
                  "|---|---|---:|---:|---:|---:|---:|"])
    for budget in BUDGETS:
        for strategy in STRATEGIES:
            m = counter["metrics_by_budget"][str(budget)][strategy]
            lines.append(f"| {budget} | {strategy} | {m['correct_resolved_n']} | {m['abstention_n']} | {m['false_authorization_n']} | {m['false_denial_n']} | {m['questions_total']} |")
    lines.extend(["", "At budget one, exact planning resolves the one identifiable denying hypothesis that greedy pair separation misses. At larger budgets it avoids questions on branches that cannot resolve. This is a post-exposure correction of a known failure, not a prospective comparison. All 18 explicit other/unsure reply checks abstain after one answer.", "",
                  "## Coverage failure remains at one question", "",
                  "| Condition | Policy | False allow / latent deny | False deny / latent allow | Correct / cases | Abstain / cases |",
                  "|---|---|---:|---:|---:|---:|"])
    for condition in ("omit_restrictive", "omit_permissive", "missing_latent_other", "unsure"):
        for strategy in STRATEGIES:
            m = summary["by_condition"][condition]["1"][strategy]
            lines.append(f"| {condition} | {strategy} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['correct_resolved_n']}/{m['n']} | {m['abstention_n']}/{m['n']} |")
    lines.extend(["", "Removing all restrictive interpretations creates permissive consensus before a question can be asked. The exact planner cannot recover missing hypotheses and preserves this failure. Equal candidate weighting is sensitive to candidate representation and is not a semantic prior. All labels remain programmatic and unreviewed by humans.", "",
                  "## Reproduce", "", "```sh", "python3 -m eiv_experiment.planner --output build/planner-check", "```", "",
                  "Use a new output directory. Raw outcomes are stored as `raw.jsonl.gz` with a zero timestamp and no embedded filename; the manifest records compressed and uncompressed SHA-256 hashes. Summaries and this analysis are deterministic. Input and current source hashes are checked against changes during execution. The original dataset checksum is verified; original source hashes are intentionally not substituted for this current-core extension. No model is invoked and no external action executes."])
    return "\n".join(lines) + "\n"


def execute(output, max_seconds=300):
    output = Path(output)
    _require(not output.exists(), "output exists; choose a fresh directory")
    _require(type(max_seconds) is int and 1 <= max_seconds <= 3600,
             "max_seconds must be an integer from 1 to 3600")
    hashes = {name: _sha(ROOT / name) for name in SOURCE_PATHS + INPUT_PATHS}
    manifest = json.loads((ROOT / INPUT_PATHS[1]).read_text())
    _require(manifest["cases_sha256"] == hashes[INPUT_PATHS[0]], "original v3 dataset checksum mismatch")
    cases = [json.loads(line) for line in (ROOT / INPUT_PATHS[0]).read_text().splitlines()]
    _require(len(cases) == manifest["case_count"] == 1440, "unexpected v3 case count")
    _require(len({case["case_id"] for case in cases}) == len(cases), "duplicate case id")
    started = time.monotonic()
    rows = []
    for case in cases:
        for budget, strategy in itertools.product(BUDGETS, STRATEGIES):
            if time.monotonic() - started > max_seconds:
                raise ValueError("evaluation time limit exceeded; no outputs were written")
            rows.append(run_case(case, strategy, budget))
    public, counter_rows, counter = evaluate_counterexample()
    summary = summarize(rows)
    _require(all(_sha(ROOT / name) == expected for name, expected in hashes.items()),
             "inputs or current source changed during evaluation; choose a fresh run")
    output.mkdir(parents=True, exist_ok=False)
    raw_bytes = "".join(_canonical(row) + "\n" for row in rows).encode("utf-8")
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=compressed, mode="wb", mtime=0, compresslevel=9) as archive:
        archive.write(raw_bytes)
    (output / "raw.jsonl.gz").write_bytes(compressed.getvalue())
    artifacts = {
        "summary.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
        "counterexample-case.json": json.dumps(public, indent=2, sort_keys=True) + "\n",
        "counterexample-raw.jsonl": "".join(_canonical(row) + "\n" for row in counter_rows),
        "counterexample-summary.json": json.dumps(counter, indent=2, sort_keys=True) + "\n",
        "analysis.md": markdown(summary, counter),
    }
    for name, content in artifacts.items():
        (output / name).write_text(content)
    receipt = {"schema": SCHEMA, "kind": "post_hoc_current_core_extension_not_held_out",
               "input_and_source_hashes": hashes, "case_count": len(cases),
               "records": len(rows), "counterexample_records": len(counter_rows),
               "human_labels_reviewed": False, "model_calls": 0,
               "raw_uncompressed_sha256": hashlib.sha256(raw_bytes).hexdigest(),
               "raw_uncompressed_bytes": len(raw_bytes),
               "compression": "gzip level 9, mtime 0, empty filename",
               "output_hashes": {name: _sha(output / name) for name in ["raw.jsonl.gz", *artifacts]}}
    (output / "manifest.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return summary, counter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=300)
    args = parser.parse_args()
    started = time.monotonic()
    try:
        summary, counter = execute(args.output, args.max_seconds)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"cases": summary["case_count"], "records": summary["records"],
                      "counterexample_records": counter["records"],
                      "elapsed_seconds": round(time.monotonic() - started, 3),
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
