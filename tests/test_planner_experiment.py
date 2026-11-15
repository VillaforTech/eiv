"""Verify the post-hoc current-core evaluation boundary and objective counts."""

from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eiv_experiment.planner import (
    BUDGETS, ROOT, STRATEGIES, evaluate_counterexample, execute, run_case, summarize,
)


class PlannerExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = [json.loads(line) for line in (ROOT / "benchmark/v3/cases.jsonl").read_text().splitlines()]

    def test_counterexample_integrated_core_matches_exact_objective(self):
        _, rows, result = evaluate_counterexample()
        self.assertEqual(len(rows), 96)
        self.assertEqual(len(result["nonselecting_answer_checks"]), 18)
        for budget in (1, 2, 3):
            optimal = result["metrics_by_budget"][str(budget)]["optimal"]
            self.assertEqual((optimal["correct_resolved_n"], optimal["questions_total"]), (1, 8))
        self.assertEqual(result["metrics_by_budget"]["1"]["targeted"]["correct_resolved_n"], 0)

    def test_driver_preserves_coverage_failure_and_nonselecting_abstention(self):
        for condition, decision in (("omit_restrictive", "allow"), ("omit_permissive", "deny"),
                                    ("missing_latent_other", "abstain"), ("unsure", "abstain")):
            case = next(c for c in self.cases if c["condition"] == condition)
            for strategy in STRATEGIES:
                row = run_case(case, strategy, 1)
                self.assertEqual(row["decision"], decision)
                self.assertLessEqual(row["questions"], 1)
        self.assertTrue(run_case(next(c for c in self.cases if c["condition"] == "omit_restrictive"),
                                 "optimal", 1)["false_authorization"])

    def test_latent_labels_never_enter_core_input(self):
        from eiv.permissions import analyze_request
        case = deepcopy(next(c for c in self.cases if c["condition"] == "complete"))
        observed = []
        def checked(public, *args, **kwargs):
            self.assertEqual(public, case["public"])
            self.assertNotIn("oracle", public)
            self.assertNotIn("gold_decision", public)
            observed.append(deepcopy(public))
            return analyze_request(public, *args, **kwargs)
        with patch("eiv_experiment.planner.analyze_request", side_effect=checked):
            run_case(case, "optimal", 1)
        self.assertEqual(len(observed), 2)

    def test_summary_rejects_duplicate_and_missing_combinations(self):
        case = next(c for c in self.cases if c["condition"] == "complete")
        rows = [run_case(case, strategy, budget) for strategy, budget in itertools.product(STRATEGIES, BUDGETS)]
        self.assertEqual(summarize(rows)["records"], 12)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(rows + [rows[0]])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            summarize(rows[:-1])

    def test_existing_outputs_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing"
            path.mkdir()
            marker = path / "marker.txt"
            marker.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "fresh directory"):
                execute(path)
            self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
