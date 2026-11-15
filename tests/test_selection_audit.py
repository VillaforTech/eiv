"""Check evidence completeness, independent denotation and score misalignment."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from eiv.permissions import analyze_request, validate_case
from eiv_experiment.dimensions import summarize
from eiv_experiment.selection_audit import (
    ROOT, audit_v2, audit_v3, counterexample_case, operation_membership,
    read_jsonl, run_counterexample,
)


class SelectionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v2_cases = read_jsonl(ROOT / "benchmark/v2/cases.jsonl")
        cls.v2_rows = read_jsonl(ROOT / "results/engineering-v2/raw.jsonl")
        cls.v2_summary = json.loads((ROOT / "results/engineering-v2/summary.json").read_text())
        cls.v3_cases = read_jsonl(ROOT / "benchmark/v3/cases.jsonl")
        cls.v3_rows = read_jsonl(ROOT / "results/dimensions-v3/raw.jsonl")
        cls.v3_summary = json.loads((ROOT / "results/dimensions-v3/summary.json").read_text())

    def small_v3(self):
        case = next(case for case in self.v3_cases if case["condition"] == "complete")
        rows = [row for row in self.v3_rows if row["case_id"] == case["case_id"]]
        return [deepcopy(case)], deepcopy(rows), summarize(rows)

    def test_all_preserved_v2_and_v3_evidence_matches_separate_audit(self):
        v2 = audit_v2(self.v2_cases, self.v2_rows, self.v2_summary)
        v3 = audit_v3(self.v3_cases, self.v3_rows, self.v3_summary)
        self.assertEqual((v2["labels_checked"], v2["records_checked"]), (72, 240))
        self.assertEqual((v3["labels_checked"], v3["records_checked"]), (1440, 28800))

    def test_duplicate_or_missing_outcomes_rejected_before_aggregation(self):
        with self.assertRaisesRegex(ValueError, "missing, duplicate or extra"):
            audit_v2(self.v2_cases, self.v2_rows[:-1] + [self.v2_rows[0]], self.v2_summary)
        cases, rows, summary = self.small_v3()
        with self.assertRaisesRegex(ValueError, "missing, duplicate or extra"):
            audit_v3(cases, rows[:-1], summary)

    def test_independent_denotation_rejects_corrupted_programmatic_gold(self):
        cases = deepcopy(self.v2_cases)
        cases[0]["expected_decision"] = "allow" if cases[0]["expected_decision"] == "deny" else "deny"
        with self.assertRaisesRegex(ValueError, "label disagrees"):
            audit_v2(cases, self.v2_rows, self.v2_summary)

    def test_v3_answer_trace_and_disclosure_tampering_rejected(self):
        for field in ("oracle_access", "dimension_answer_disclosures"):
            cases, rows, summary = self.small_v3()
            row = next(row for row in rows if row["arm"] == "eiv_targeted" and row["budget"] == 1)
            if field == "oracle_access":
                row[field][0]["answer"] = "v1" if row[field][0]["answer"] == "v0" else "v0"
            else:
                row[field] = 0
            with self.assertRaises(ValueError):
                audit_v3(cases, rows, summary)

    def test_v3_stratified_denominator_tampering_rejected(self):
        cases, rows, summary = self.small_v3()
        summary["by_condition"]["complete"]["1"]["eiv_targeted"]["latent_deny_n"] += 1
        with self.assertRaisesRegex(ValueError, "metric mismatch"):
            audit_v3(cases, rows, summary)

    def test_budget_counterexample_runs_real_core_and_matches_explicit_counts(self):
        case, rows, summary = run_counterexample()
        validate_case(case)
        self.assertEqual(len(rows), 48)
        self.assertEqual(summary["question_scores"], {"isolate": 4, "balanced": 8})
        self.assertEqual(summary["one_step_resolution_choice"], "isolate")
        self.assertEqual({row["question"]: row["immediately_resolved_candidates"] for row in summary["root_question_diagnostics"]},
                         {"isolate": 1, "balanced": 0})
        one = summary["counts_by_budget"]["1"]
        self.assertEqual((one["targeted"]["correct_resolved_n"], one["first"]["correct_resolved_n"]), (0, 1))
        self.assertEqual((one["targeted"]["false_authorization_n"], one["first"]["false_authorization_n"]), (0, 0))
        self.assertTrue(all(row["decision"] == row["expected_terminal_decision"] for row in rows))
        self.assertEqual(len(summary["other_unsure_checks"]), 8)

    def test_candidate_renaming_does_not_remove_the_strict_score_counterexample(self):
        case = counterexample_case()
        renaming = {candidate["id"]: "policy_" + str(71 - index * 3) for index, candidate in enumerate(case["candidates"])}
        for candidate in case["candidates"]:
            candidate["id"] = renaming[candidate["id"]]
        for question in case["questions"]:
            for answer in question["answers"]:
                answer["retain"] = [renaming[cid] for cid in answer["retain"]]
        self.assertEqual(analyze_request(case, max_questions=1)["suggested_question"]["id"], "balanced")
        self.assertEqual(analyze_request(case, max_questions=1, question_strategy="first")["suggested_question"]["id"], "isolate")

    def test_operation_reference_preserves_unknowns_scope_and_contradiction(self):
        case = counterexample_case()
        request, facts = deepcopy(case["request"]), {}
        policy = deepcopy(case["candidates"][0])
        request["scope"] = "session"
        self.assertEqual(operation_membership(request, facts, policy), "deny")
        policy["permissions"][0]["scope"] = "session"
        self.assertEqual(operation_membership(request, facts, policy), "allow")
        policy["permissions"][0]["conditions"] = {"approved": True}
        self.assertEqual(operation_membership(request, facts, policy), "abstain")
        facts["approved"] = True
        self.assertEqual(operation_membership(request, facts, policy), "allow")
        deny = deepcopy(policy["permissions"][0])
        deny["effect"] = "deny"
        deny["scope"] = "once"
        policy["permissions"].append(deny)
        self.assertEqual(operation_membership(request, facts, policy), "abstain")


if __name__ == "__main__":
    unittest.main()
