"""Check exact finite planning against exhaustive policy-tree enumeration."""

from copy import deepcopy
import itertools
import random
import unittest

from eiv.logic import ValidationError
from eiv.permissions import _question, evaluate_candidate
from eiv.planning import PlanningLimitError, plan_questions, select_question
from eiv_experiment.selection_audit import counterexample_case


def question(name, groups):
    return {"id": name, "prompt": "Choose the intended group.", "answers": [
        {"id": "a" + str(i), "label": "Group " + str(i), "retain": group}
        for i, group in enumerate(groups)]}


def exhaustive_reference(questions, decisions, active, budget):
    """Enumerate complete legal policy trees, without bit masks or caching."""
    if active and {decisions[cid] for cid in active} in ({"allow"}, {"deny"}):
        return len(active), 0, None
    alternatives = [(0, 0, None)]  # stop and abstain
    if budget:
        for q in questions:
            groups = [set(answer["retain"]).intersection(active) for answer in q["answers"]]
            groups = [group for group in groups if group]
            if len(groups) < 2:
                continue
            child = [exhaustive_reference(questions, decisions, group, budget - 1)
                     for group in groups]
            alternatives.append((sum(x[0] for x in child),
                                 len(active) + sum(x[1] for x in child), q["id"]))
    # max() is stable, preserving stop/input order on exact ties.
    return max(alternatives, key=lambda x: (x[0], -x[1]))


class PlanningTests(unittest.TestCase):
    def test_all_four_candidate_decision_assignments_match_exhaustive_oracle(self):
        ids = ["c0", "c1", "c2", "c3"]
        qs = [question("left", [ids[:2], ids[2:]]),
              question("parity", [ids[::2], ids[1::2]]),
              question("singleton", [ids[:1], ids[1:]])]
        for decisions in itertools.product(("allow", "deny", "abstain"), repeat=4):
            rows = [{"id": cid, "decision": decision} for cid, decision in zip(ids, decisions)]
            mapping = dict(zip(ids, decisions))
            for budget in range(4):
                with self.subTest(decisions=decisions, budget=budget):
                    actual = plan_questions(qs, rows, ids, budget)
                    expected = exhaustive_reference(qs, mapping, set(ids), budget)
                    self.assertEqual((actual["resolved_candidates"], actual["total_questions"],
                                      actual["suggested_question"]["id"] if actual["suggested_question"] else None),
                                     expected)

    def test_multivalued_partitions_and_active_subsets_match_exhaustive_oracle(self):
        rng = random.Random(7183)
        for trial in range(60):
            ids = ["c" + str(i) for i in range(rng.randint(2, 6))]
            rows = [{"id": cid, "decision": rng.choice(("allow", "deny", "abstain"))}
                    for cid in ids]
            qs = []
            for i in range(4):
                group_count = rng.randint(2, len(ids))
                shuffled = rng.sample(ids, len(ids))
                groups = [shuffled[j::group_count] for j in range(group_count)]
                qs.append(question("q" + str(i), groups))
            active = rng.sample(ids, rng.randint(1, len(ids)))
            for budget in range(4):
                actual = plan_questions(qs, rows, active, budget)
                expected = exhaustive_reference(qs, {r["id"]: r["decision"] for r in rows},
                                                set(active), budget)
                self.assertEqual((actual["resolved_candidates"], actual["total_questions"],
                                  actual["suggested_question"]["id"] if actual["suggested_question"] else None),
                                 expected, (trial, budget))

    def test_recovers_one_resolved_hypothesis_in_published_greedy_counterexample(self):
        case = counterexample_case()
        rows = [evaluate_candidate(case["request"], case["facts"], candidate)
                for candidate in case["candidates"]]
        ids = [row["id"] for row in rows]
        self.assertEqual(_question(case["questions"], rows, ids, "targeted")["id"], "balanced")
        plan = plan_questions(case["questions"], rows, ids, 1)
        self.assertEqual(plan["suggested_question"]["id"], "isolate")
        self.assertEqual((plan["resolved_candidates"], plan["candidate_count"], plan["total_questions"]),
                         (1, 8, 8))
        self.assertEqual(plan["coverage"], "unverified")

    def test_lookahead_finds_benefit_without_immediate_pure_answer(self):
        ids = ["c0", "c1", "c2", "c3"]
        rows = [{"id": cid, "decision": decision} for cid, decision in
                zip(ids, ("allow", "deny", "deny", "allow"))]
        qs = [question("first", [ids[:2], ids[2:]]),
              question("second", [ids[::2], ids[1::2]])]
        self.assertIsNone(select_question(qs, rows, ids, 1))
        plan = plan_questions(qs, rows, ids, 2)
        self.assertEqual((plan["resolved_candidates"], plan["total_questions"]), (4, 8))
        self.assertEqual(plan["suggested_question"]["id"], "first")

    def test_secondary_objective_skips_unproductive_questions(self):
        ids = ["a", "b", "c", "d"]
        rows = [{"id": cid, "decision": "allow" if cid == "a" else "abstain"} for cid in ids]
        qs = [question("indirect", [["a", "b"], ["c", "d"]]),
              question("direct", [["a"], ["b", "c", "d"]])]
        plan = plan_questions(qs, rows, ids, 2)
        self.assertEqual(plan["suggested_question"]["id"], "direct")
        self.assertEqual((plan["resolved_candidates"], plan["total_questions"]), (1, 4))
        self.assertIsNone(select_question(qs, rows, ["b", "c", "d"], 1))

    def test_only_known_unanimous_decisions_count_as_resolved(self):
        ids = ["a", "b"]
        qs = [question("split", [["a"], ["b"]])]
        for state in ("allow", "deny", "abstain"):
            rows = [{"id": cid, "decision": state} for cid in ids]
            plan = plan_questions(qs, rows, ids, 8)
            self.assertIsNone(plan["suggested_question"])
            self.assertEqual(plan["resolved_candidates"], 0 if state == "abstain" else 2)
            self.assertEqual(plan["total_questions"], 0)
        self.assertEqual(plan_questions([], [], [], 0)["resolved_candidates"], 0)

    def test_input_order_ties_and_copy_isolation(self):
        rows = [{"id": "a", "decision": "allow"}, {"id": "b", "decision": "deny"}]
        qs = [question("earlier", [["a"], ["b"]]), question("later", [["b"], ["a"]])]
        original = deepcopy(qs)
        result = select_question(qs, rows, ["b", "a"], 2)
        self.assertEqual(result["id"], "earlier")
        result["answers"][0]["retain"].append("mutated")
        self.assertEqual(qs, original)
        self.assertEqual(select_question(list(reversed(qs)), rows, ["a", "b"], 2)["id"], "later")

    def test_previously_selected_partition_cannot_be_reasked(self):
        ids = ["a", "b", "c"]
        rows = [{"id": cid, "decision": "deny" if cid == "c" else "allow"} for cid in ids]
        qs = [question("past", [["a"], ["b", "c"]]),
              question("useful", [["a", "b"], ["c"]])]
        self.assertEqual(select_question(qs, rows, ["b", "c"], 1)["id"], "useful")

    def test_work_exhaustion_does_not_return_partial_plan(self):
        rows = [{"id": "a", "decision": "allow"}, {"id": "b", "decision": "deny"}]
        qs = [question("q0", [["a"], ["b"]]), question("q1", [["a"], ["b"]])]
        with self.assertRaisesRegex(PlanningLimitError, "state limit"):
            plan_questions(qs, rows, ["a", "b"], 1, max_states=1)
        with self.assertRaisesRegex(PlanningLimitError, "transition limit"):
            plan_questions(qs, rows, ["a", "b"], 1, max_transitions=1)

    def test_malformed_inputs_rejected_before_search(self):
        rows = [{"id": "a", "decision": "allow"}, {"id": "b", "decision": "deny"}]
        qs = [question("q", [["a"], ["b"]])]
        invalid = [([], rows, ["a", "a"], 1), ([], rows, ["missing"], 1),
                   ([], rows + [rows[0]], ["a"], 1), ([], rows, ["a"], True),
                   ([], rows, ["a"], 9), ([], [{"id": "a", "decision": []}], ["a"], 1),
                   ([question("q", [["a"], ["a", "b"]])], rows, ["a"], 1),
                   ([question("q", [["a"], ["missing"]])], rows, ["a"], 1),
                   (qs + qs, rows, ["a"], 1)]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValidationError):
                plan_questions(*args)
        for cap in (True, 0, 1000001, 1.5):
            with self.assertRaises(ValidationError):
                plan_questions(qs, rows, ["a", "b"], 1, max_states=cap)

    def test_sixteen_candidate_complete_partition(self):
        ids = ["c" + str(i) for i in range(16)]
        rows = [{"id": cid, "decision": "allow" if i % 2 else "deny"}
                for i, cid in enumerate(ids)]
        plan = plan_questions([question("identify", [[cid] for cid in ids])], rows, ids, 8)
        self.assertEqual((plan["resolved_candidates"], plan["total_questions"]), (16, 16))
        self.assertLessEqual(plan["states_evaluated"], 17)


if __name__ == "__main__":
    unittest.main()
