import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from eiv_experiment.replay import ARMS as MODEL_ARMS, export_requests, oracle_disclosure, public_packet, validate_replay
from eiv_experiment.run import ROOT, answer_for, covers, generate_fixture, load_cases, metrics, paired, permission_key, run_one, verify_freeze


class BenchmarkTests(unittest.TestCase):
    def test_frozen_inputs_have_exact_hashes(self):
        self.assertEqual(verify_freeze()["counts"], {"dev": 24, "validation": 8, "test": 40})
        self.assertEqual(verify_freeze("1")["counts"], {"dev": 32, "validation": 16, "test": 24})

    def test_no_family_or_template_crosses_splits(self):
        cases = load_cases()
        self.assertEqual(len({c["case_id"] for c in cases}), 72)
        for field in ("family", "template_id"):
            groups = {}
            for case in cases: groups.setdefault(case[field], set()).add(case["split"])
            self.assertEqual(len(groups), 11)
            self.assertTrue(all(len(splits) == 1 for splits in groups.values()))
        self.assertTrue(all(c["review"]["status"] == "unreviewed" for c in cases))

    def test_generator_reproduces_frozen_data(self):
        spec = importlib.util.spec_from_file_location("benchmark_generator", ROOT / "benchmark/generate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.make_cases(), load_cases(ROOT / "benchmark/cases.jsonl"))
        v2spec = importlib.util.spec_from_file_location("benchmark_generator_v2", ROOT / "benchmark/v2/build.py")
        v2module = importlib.util.module_from_spec(v2spec)
        v2spec.loader.exec_module(v2module)
        self.assertEqual(v2module.build_cases(), load_cases())

    def test_public_packet_has_no_oracle_or_labels(self):
        case = load_cases()[0]
        self.assertEqual(set(public_packet(case)), {"instruction", "request", "facts"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requests.jsonl"
            self.assertEqual(export_requests([case], path), 3)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertTrue(all(r["input"] == public_packet(case) for r in rows))
            self.assertEqual(len({r["initial_packet_sha256"] for r in rows}), 1)

    def test_oracle_rejects_budget_exhaustion(self):
        case = load_cases()[0]
        self.assertEqual(oracle_disclosure(case, 0), case["latent_intent"]["description"])
        with self.assertRaises(ValueError): oracle_disclosure(case, 1)

    def test_coverage_is_policy_not_decision_equality(self):
        case = next(c for c in load_cases() if c["scenario_family"] == "single_grant")
        candidate = case["latent_intent"]["candidate"]
        other = json.loads(json.dumps(candidate))
        other["id"] = "different"
        other["interpretation"] = "Different prose, same finite policy."
        self.assertTrue(covers([other], candidate))
        other["permissions"][0]["resources"].append("additional")
        self.assertFalse(covers([other], candidate))

    def test_direct_cannot_answer_questions(self):
        case = next(c for c in load_cases() if c["scenario_family"] == "resource_disjunction")
        row = run_one(case, "direct")
        self.assertEqual(row["questions"], 0)
        self.assertEqual(row["decision"], "abstain")

    def test_missing_intent_retains_wrong_consensus(self):
        case = next(c for c in load_cases() if c["scenario_family"] == "omitted_restrictive_reading")
        eiv = run_one(case, "eiv")
        conventional = run_one(case, "conventional")
        self.assertTrue(eiv["false_authorization"])
        self.assertFalse(eiv["initial_candidate_coverage"])
        self.assertEqual(eiv["questions"], 0)
        self.assertEqual(conventional["decision"], "abstain")
        self.assertEqual(conventional["questions"], 1)

    def test_insufficient_answer_abstains(self):
        case = next(c for c in load_cases() if c["scenario_family"] == "insufficient_answer")
        row = run_one(case, "eiv")
        self.assertEqual(row["decision"], "abstain")
        self.assertEqual(row["reason"], "insufficient_answer")

    def test_abstaining_cannot_count_as_correct(self):
        row = {"expected_decision": "deny", "decision": "abstain", "false_authorization": False,
               "false_denial": False, "correct_resolved": False, "questions": 0, "latency_seconds": 0}
        result = metrics([row])
        self.assertEqual(result["correct_resolved_rate"], 0)
        self.assertEqual(result["abstention_rate"], 1)
        self.assertIsNone(result["selective_accuracy"])
        self.assertIsNone(result["false_denial_rate"])

    def test_replay_rejects_missing_provenance_and_oracle_leak(self):
        case = load_cases()[0]
        rows = [{"case_id": case["case_id"], "arm": arm, "decision": "allow", "model": "local-fixture",
                 "model_digest": "immutable", "usage": {"calls": 1, "input_tokens": 10, "output_tokens": 10},
                 "questions": 0, "oracle_access": [], "latency_seconds": 0.1, "monetary_cost_usd": 0,
                 "raw_messages": [{"response": {"decision": "allow"}}]} for arm in MODEL_ARMS]
        validate_replay(rows, [case])
        rows[0]["questions"] = 1
        rows[0]["oracle_access"] = [{"answer": "permission"}]
        with self.assertRaises(ValueError): validate_replay(rows, [case])
        rows[0]["questions"] = 0
        rows[0]["oracle_access"] = []
        rows[0].pop("model_digest")
        with self.assertRaises(ValueError): validate_replay(rows, [case])

    def test_family_pairing_requires_complete_pairs(self):
        case = load_cases()[0]
        rows = [run_one(case, "eiv"), run_one(case, "direct")]
        result = paired(rows, "direct", repetitions=20)
        self.assertEqual(result["point"]["correct_resolved_rate"], 0)
        with self.assertRaises(ValueError): paired(rows[:1], "direct", repetitions=20)


if __name__ == "__main__": unittest.main()
