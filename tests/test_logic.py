import copy
import unittest

from eiv.fixtures import atom, build_suite, case, candidate, fact, rule, spec
from eiv.logic import ValidationError, analyze_spec, evaluate_world
from eiv.workflow import analyze_case
from eiv.benchmark import run_benchmark


def truth_clause(p, q):
    return {"and": [atom("P") if p else {"not": atom("P")},
                    atom("Q") if q else {"not": atom("Q")} ]}


def dnf(model_indices):
    clauses = [truth_clause(bool(i & 1), bool(i & 2)) for i in model_indices]
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"or": clauses}


class ExhaustiveClassificationTests(unittest.TestCase):
    def test_every_two_atom_theory_model_set_and_witness(self):
        queries = [
            (atom("P"), lambda p, q: p),
            (atom("Q"), lambda p, q: q),
            ({"implies": [atom("P"), atom("Q")]}, lambda p, q: not p or q),
            ({"iff": [atom("P"), atom("Q")]}, lambda p, q: p == q),
        ]
        # Every one of the 2^(2^2) possible model sets, under four queries.
        for subset in range(16):
            selected = [i for i in range(4) if subset & (1 << i)]
            constraints = [dnf(selected)] if selected else []
            facts = [] if selected else [fact("P", True), fact("P", False)]
            for query, independent_query in queries:
                model = spec(["Unit"], {"P": 0, "Q": 0}, facts, [], constraints, query)
                result = analyze_spec(model)
                yes = any(independent_query(bool(i & 1), bool(i & 2)) for i in selected)
                no = any(not independent_query(bool(i & 1), bool(i & 2)) for i in selected)
                expected = ("inconsistent" if not yes and not no else
                            "underdetermined" if yes and no else "entailed" if yes else "refuted")
                with self.subTest(subset=subset, query=query):
                    self.assertEqual(result["status"], expected)
                    self.assertEqual(result["theory_models"], len(selected))
                    self.assertEqual(result["sat_theory_and_query"], yes)
                    self.assertEqual(result["sat_theory_and_not_query"], no)
                    for key, query_value, exists in [
                        ("witness_query", True, yes), ("countermodel", False, no)
                    ]:
                        world = result[key]
                        self.assertEqual(world is not None, exists)
                        if world is not None:
                            checked = evaluate_world(model, world)
                            self.assertTrue(checked["satisfies_theory"])
                            self.assertEqual(checked["query_value"], query_value)
                            world_index = int(world["P"]) + 2 * int(world["Q"])
                            self.assertIn(world_index, selected)
                            self.assertEqual(independent_query(world["P"], world["Q"]), query_value)

    def test_universal_finite_domain_rule(self):
        model = spec(["Ana", "Ben"], {"P": 1, "Q": 1},
                     [fact("P", True, "Ana"), fact("P", True, "Ben")],
                     [rule(["?x"], atom("P", "?x"), atom("Q", "?x"))],
                     [], {"and": [atom("Q", "Ana"), atom("Q", "Ben")]})
        self.assertEqual(analyze_spec(model)["status"], "entailed")

    def test_resource_limit_is_unknown_not_underdetermined(self):
        model = spec(["A", "B", "C", "D"], {"P": 1}, [], [], [], atom("P", "A"))
        result = analyze_spec(model, max_atoms=3)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["assignments_examined"], 0)
        self.assertIsNone(result["sat_theory_and_query"])

    def test_rejects_unbound_variable_and_incomplete_world(self):
        model = spec(["Ana"], {"P": 1}, [], [], [], atom("P", "?x"))
        with self.assertRaises(ValidationError):
            analyze_spec(model)
        model["query"] = atom("P", "Ana")
        with self.assertRaises(ValidationError):
            evaluate_world(model, {})


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = {item["id"]: item for item in build_suite()}

    def test_necessary_sufficient_and_explicit_clarification(self):
        case_data = self.items["necessary_vs_sufficient"]["case"]
        before = analyze_case(case_data)
        self.assertEqual(before["action"], "ask")
        self.assertEqual([c["result"]["status"] for c in before["candidates"]],
                         ["underdetermined", "entailed"])
        after_yes = analyze_case(case_data, {"question": "payment_rule", "answer": "yes"})
        self.assertEqual((after_yes["action"], after_yes["answer"]), ("answer", "yes"))
        self.assertEqual(after_yes["clarification"]["after"], ["sufficient"])
        self.assertEqual(after_yes["excluded_candidates"][0]["candidate"], "necessary")
        after_no = analyze_case(case_data, {"question": "payment_rule", "answer": "no"})
        self.assertEqual(after_no["action"], "underdetermined")

    def test_inconsistent_candidate_remains_visible_until_clarified(self):
        case_data = self.items["inconsistent_candidate"]["case"]
        result = analyze_case(case_data)
        self.assertEqual(result["action"], "ask")
        self.assertEqual(result["candidates"][0]["result"]["status"], "inconsistent")
        self.assertEqual(result["excluded_candidates"], [])
        clarified = analyze_case(case_data, {"question": "typo", "answer": "yes"})
        self.assertEqual(clarified["answer"], "yes")
        self.assertEqual(clarified["candidates"][0]["result"]["status"], "inconsistent")
        self.assertFalse(clarified["candidates"][0]["active"])

    def test_irrelevant_ambiguity_needs_no_question(self):
        result = analyze_case(self.items["irrelevant_ambiguity"]["case"])
        self.assertEqual(result["answer"], "yes")
        self.assertIsNone(result["suggested_question"])

    def test_invalid_question_partition_rejected(self):
        case_data = copy.deepcopy(self.items["necessary_vs_sufficient"]["case"])
        case_data["questions"][0]["answers"][1]["retain"] = ["sufficient"]
        with self.assertRaises(ValidationError):
            analyze_case(case_data)

    def test_unreviewed_adapter_is_rejected(self):
        case_data = copy.deepcopy(self.items["simple_entailed"]["case"])
        case_data["source_type"] = "unreviewed_adapter_proposal"
        with self.assertRaises(ValidationError):
            analyze_case(case_data)

    def test_benchmark_reproduces_coverage_failure_and_holdout(self):
        first, second = run_benchmark(), run_benchmark()
        self.assertEqual(first, second)
        self.assertEqual(first["overall"]["wrong_emitted_answers"], 1)
        self.assertEqual(first["overall"]["questions_asked"], 2)
        self.assertEqual(first["by_split"]["structural_holdout"]["cases"], 5)
        self.assertEqual(first["by_split"]["structural_holdout"]["wrong_emitted_answers"], 1)
        failure = next(row for row in first["cases"] if row["id"] == "candidate_coverage_failure")
        self.assertEqual((failure["emitted_answer"], failure["oracle_answer"]), ("yes", "no"))
        self.assertEqual(failure["split"], "structural_holdout")


if __name__ == "__main__":
    unittest.main()
