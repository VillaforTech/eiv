"""Deterministic fixture benchmark with an oracle excluded from inference."""

from .fixtures import build_suite
from .logic import analyze_spec
from .workflow import analyze_case


def _metrics(rows):
    answerable = sum(row["oracle_status"] in ("entailed", "refuted") for row in rows)
    emissions = [row for row in rows if row["emitted_answer"] is not None]
    answered_answerable = sum(row["emitted_answer"] is not None
                              for row in rows if row["oracle_answer"] is not None)
    correct_answerable = sum(row["emitted_answer"] == row["oracle_answer"]
                             for row in rows if row["oracle_answer"] is not None and row["emitted_answer"] is not None)
    return {"cases": len(rows), "answerable_cases": answerable,
            "emitted_answers": len(emissions),
            "answerable_coverage": answered_answerable / answerable if answerable else None,
            "correct_answerable_rate": correct_answerable / answerable if answerable else None,
            "emission_rate": len(emissions) / len(rows) if rows else None,
            "wrong_emitted_answers": sum(row["emitted_answer"] != row["oracle_answer"] for row in emissions),
            "questions_asked": sum(row["action"] == "ask" for row in rows),
            "underdetermined_outputs": sum(row["action"] == "underdetermined" for row in rows),
            "blocked_outputs": sum(row["action"].startswith("blocked") for row in rows)}


def run_benchmark():
    rows = []
    for item in build_suite():
        oracle = analyze_spec(item["oracle_spec"])
        if oracle["status"] == "unknown":
            raise RuntimeError("benchmark oracle exceeded evaluation budget")
        prediction = analyze_case(item["case"])
        gold_answer = {"entailed": "yes", "refuted": "no"}.get(oracle["status"])
        rows.append({"id": item["id"], "split": item["split"],
                     "oracle_status": oracle["status"], "oracle_answer": gold_answer,
                     "action": prediction["action"], "emitted_answer": prediction["answer"],
                     "candidate_statuses": {c["id"]: c["result"]["status"] for c in prediction["candidates"]}})
    splits = sorted(set(row["split"] for row in rows))
    return {"benchmark_id": "eiv-fixture-v1", "method": "manual_fixture_formal_core",
            "natural_language_parsing_evaluated": False,
            "llm_baseline": None,
            "split_note": "The structural_holdout key marks hand-built structural challenge fixtures, including candidate_coverage_failure. It is not a blind empirical holdout study.",
            "metric_definitions": {
                "answerable_coverage": "Yes/no emissions on oracle entailed/refuted cases divided by those cases, regardless of correctness.",
                "correct_answerable_rate": "Correct yes/no emissions divided by oracle entailed/refuted cases.",
                "emission_rate": "Yes/no emissions divided by all cases.",
                "wrong_emitted_answers": "Yes/no emissions unequal to oracle yes/no, including emission on nonanswerable cases.",
                "questions_asked": "Cases requesting one predeclared distinguishing question."
            },
            "overall": _metrics(rows),
            "by_split": {split: _metrics([row for row in rows if row["split"] == split]) for split in splits},
            "cases": rows}
