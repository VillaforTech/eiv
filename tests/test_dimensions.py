"""Mechanism and label-boundary checks for the separate exposed v3 study."""
from copy import deepcopy
import itertools
import unittest

from eiv.logic import ValidationError
from eiv.permissions import analyze_request, evaluate_candidate, validate_case
from eiv_experiment.dimensions import (
    ARMS, generate_cases, dimension_answer, metrics, policy_step, run_one, select_question,
)


class DimensionStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = generate_cases()

    def complete(self, family="resource", order=(1, 2, 0), latent="101"):
        return next(c for c in self.cases if c["family"] == family and c["condition"] == "complete"
                    and c["question_order"] == list(order) and c["oracle"]["latent_candidate_id"] == "c" + latent)

    def checks(self, case):
        public = case["public"]
        return [evaluate_candidate(public["request"], public["facts"], c) for c in public["candidates"]]

    def test_generation_is_complete_unique_counterbalanced_and_structurally_valid(self):
        self.assertEqual(len(self.cases), 1440)
        self.assertEqual(len({c["case_id"] for c in self.cases}), 1440)
        self.assertEqual(self.cases, generate_cases())
        for case in self.cases:
            validate_case(case["public"])
        for position in (0, 1, 2):
            self.assertEqual(sum(c["question_order"].index(0) == position for c in self.cases), 480)

    def test_programmatic_gold_agrees_with_independent_complete_set_denotation(self):
        # Independent exact operation membership, without production dimensions,
        # compiler, parser, select_question or candidate-ID meaning.
        for family in {c["family"] for c in self.cases}:
            for bits in itertools.product("01", repeat=3):
                case = self.complete(family=family, latent="".join(bits))
                request, facts = case["public"]["request"], case["public"]["facts"]
                policy = next(c for c in case["public"]["candidates"] if c["id"] == case["oracle"]["latent_candidate_id"])
                memberships = {"allow": False, "deny": False}
                for permission in policy["permissions"]:
                    actual = (request["action"], request["resource"], request["recipient"], request["scope"])
                    scopes = ("once", "session") if permission["effect"] == "deny" or permission["scope"] == "session" else ("once",)
                    relation = set(itertools.product([permission["action"]], permission["resources"], permission["recipients"], scopes))
                    condition_true = all(facts.get(name) == truth for name, truth in permission["conditions"].items())
                    memberships[permission["effect"]] |= actual in relation and condition_true
                expected = "allow" if memberships["allow"] and not memberships["deny"] else "deny"
                self.assertEqual(case["gold_decision"], expected)

    def test_targeted_and_first_exactly_replay_original_core_across_question_orders(self):
        for order in itertools.permutations(range(3)):
            case = self.complete(order=order)
            checks = self.checks(case)
            for arm, strategy in [("eiv_targeted", "targeted"), ("ordinary_first", "first")]:
                answers = []
                for _ in range(4):
                    result = policy_step(case["public"], checks, answers, 3, arm)
                    original = analyze_request(case["public"], answers, max_questions=3, question_strategy=strategy)
                    self.assertEqual(result["decision"], original["decision"])
                    self.assertEqual(result["active_candidate_ids"], original["active_candidate_ids"])
                    self.assertEqual(result["questions_used"], original["questions_used"])
                    if result["decision"] != "ask":
                        break
                    question = result["suggested_question"]["question"]
                    self.assertEqual(question, original["suggested_question"])
                    answers.append({"question": question["id"], "answer": dimension_answer(question, case["oracle"])})

    def test_targeted_uses_one_answer_while_first_preserves_order_cost_and_ties(self):
        for order in itertools.permutations(range(3)):
            case = self.complete(order=order)
            target = run_one(case, "eiv_targeted", 3)
            first = run_one(case, "ordinary_first", 3)
            fixed = run_one(case, "fixed_order", 3)
            self.assertEqual(target["questions"], 1)
            self.assertEqual(first["questions"], order.index(0) + 1)
            self.assertEqual(first, dict(fixed, arm="ordinary_first"))
            self.assertTrue(target["correct_resolved"] and first["correct_resolved"])
            self.assertEqual(target["dimension_answer_disclosures"], target["questions"])

    def test_budget_and_noninteractive_controls_never_access_oracle(self):
        case = self.complete()
        for arm in ARMS:
            row = run_one(case, arm, 0)
            self.assertEqual((row["decision"], row["questions"], row["oracle_access"]), ("abstain", 0, []))
        for arm in ("direct", "abstain_all"):
            self.assertEqual(run_one(case, arm, 3)["questions"], 0)
        self.assertEqual(run_one(case, "ordinary_first", 1)["decision"], "abstain")

    def test_omission_retains_false_consensus_and_does_not_trigger_oracle(self):
        for condition, latent, decision, error in [("omit_restrictive", "000", "allow", "false_authorization"),
                                                   ("omit_permissive", "100", "deny", "false_denial")]:
            case = next(c for c in self.cases if c["condition"] == condition and c["oracle"]["latent_candidate_id"] == "c" + latent)
            for arm in ARMS[:-1]:
                row = run_one(case, arm, 3)
                self.assertEqual((row["decision"], row["questions"], row[error]), (decision, 0, True))
                self.assertFalse(row["initial_candidate_coverage"])

    def test_other_unsure_are_terminal_and_never_select_a_binary_dimension(self):
        for condition, answer in [("unsure", "unsure"), ("missing_latent_other", "other")]:
            case = next(c for c in self.cases if c["condition"] == condition)
            for arm in ("ordinary_first", "fixed_order", "eiv_targeted"):
                row = run_one(case, arm, 3)
                self.assertEqual((row["decision"], row["questions"], row["dimension_answer_disclosures"]), ("abstain", 1, 0))
                self.assertEqual(row["oracle_access"][0]["answer"], answer)
                self.assertEqual(row["trace"][0]["before"], row["trace"][0]["after"])

    def test_policy_selection_has_no_latent_label_or_condition_access(self):
        case = self.complete()
        changed = deepcopy(case)
        changed["gold_decision"] = "deny"
        changed["oracle"]["dimensions"] = [0, 0, 0]
        changed["condition"] = "invented metadata"
        changed["initial_candidate_coverage"] = False
        checks = self.checks(case)
        # Public data is the entire policy interface; hidden mutations never enter.
        self.assertEqual(policy_step(case["public"], checks, [], 1, "eiv_targeted"),
                         policy_step(changed["public"], checks, [], 1, "eiv_targeted"))
        question = select_question(case["public"]["questions"], checks, [c["id"] for c in case["public"]["candidates"]], "targeted")
        answer = dimension_answer(question["question"], changed["oracle"])
        self.assertEqual(answer, "v0")
        self.assertNotIn("gold", answer)

    def test_missing_checks_and_unsolicited_or_repeated_answers_cannot_authorize(self):
        case = self.complete()
        with self.assertRaises(ValidationError):
            policy_step(case["public"], [], [], 1, "eiv_targeted")
        for answers in [[{"question": "d2", "answer": "v1"}],
                        [{"question": "d0", "answer": "other"}, {"question": "d1", "answer": "v0"}]]:
            with self.assertRaises(ValidationError):
                policy_step(case["public"], self.checks(case), answers, 3, "eiv_targeted")

    def test_metrics_preserve_denominators_and_do_not_reward_abstention(self):
        case = self.complete()
        correct = run_one(case, "eiv_targeted", 1)
        abstain = run_one(case, "abstain_all", 1)
        result = metrics([correct, abstain])
        self.assertEqual((result["n"], result["correct_resolved_n"], result["abstention_n"]), (2, 1, 1))
        self.assertEqual(result["correct_resolved_rate"], .5)
        self.assertEqual(result["selective_accuracy"], 1)
        self.assertEqual(result["dimension_answer_disclosures"], 1)
        self.assertIsNone(result["false_authorization_rate"])


if __name__ == "__main__":
    unittest.main()
