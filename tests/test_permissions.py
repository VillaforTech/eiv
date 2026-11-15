"""Engineering tests; these do not estimate general-language safety."""

from copy import deepcopy
from itertools import product
import json
import unittest

from eiv.logic import ValidationError, evaluate_world
from eiv.permissions import (
    analyze_request, evaluate_candidate, load_structured_case, parse_instruction,
    start_session, step_session, validate_case,
)


def request(domain="files", action="read", resource="report", recipient=None, scope="once"):
    return dict(domain=domain, action=action, resource=resource, recipient=recipient, scope=scope)


def packet(text="You may read report once.", facts=None, operation=None):
    return parse_instruction(text, operation or request(), facts or {})


class PermissionUnitTests(unittest.TestCase):
    def test_explicit_grant_has_independently_checkable_witness(self):
        case = packet()
        result = analyze_request(case)
        self.assertEqual(result["decision"], "allow")
        row = result["candidates"][0]
        evidence = evaluate_world(row["formal_spec"], row["formal_result"]["witness_query"])
        self.assertEqual(evidence, {"satisfies_theory": True, "query_value": True})
        self.assertEqual(result["coverage"], "unverified")
        self.assertTrue(result["simulated"])

    def test_partial_resource_action_recipient_and_scope_permissions(self):
        for operation in [request(action="delete"), request(resource="payroll"), request(scope="session")]:
            with self.subTest(operation=operation):
                self.assertEqual(analyze_request(packet(operation=operation))["decision"], "deny")
        operation = request("messages", "send", "report", "bea")
        case = packet("You may send report to alex once.", operation=operation)
        self.assertEqual(analyze_request(case)["decision"], "deny")
        case = packet("You may read report for this session.")
        self.assertEqual(analyze_request(case)["decision"], "allow")

    def test_conditions_false_deny_and_unknown_abstain(self):
        text = "You may read report once if approved is true."
        self.assertEqual(analyze_request(packet(text, {"approved": True}))["decision"], "allow")
        self.assertEqual(analyze_request(packet(text, {"approved": False}))["decision"], "deny")
        result = analyze_request(packet(text))
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["candidates"][0]["reason"], "unknown_condition")

    def test_unknown_irrelevant_condition_does_not_block(self):
        case = packet("You may read report once; You may delete payroll once if approved is true.")
        self.assertEqual(analyze_request(case)["decision"], "allow")

    def test_negation_exception_and_contradiction(self):
        self.assertEqual(analyze_request(packet("You must not read report once."))["decision"], "deny")
        text = "You may read report once unless classified is true."
        self.assertEqual(analyze_request(packet(text, {"classified": False}))["decision"], "allow")
        self.assertEqual(analyze_request(packet(text, {"classified": True}))["decision"], "deny")
        case = packet("You may read report once; You must not read report once.")
        result = analyze_request(case)
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["candidates"][0]["formal_result"]["status"], "inconsistent")

    def test_empty_permission_set_is_closed_world_denial(self):
        case = packet()
        case["candidates"][0]["permissions"] = []
        self.assertEqual(analyze_request(case)["decision"], "deny")

    def test_unsupported_language_and_candidate_explosion_abstain(self):
        for text in ["Share the usual thing with whoever needs it.",
                     "You may send report or payroll to alex or bea once or for this session."]:
            case = packet(text, operation=request("messages", "send", "report", "alex"))
            self.assertEqual(case["semantic_status"], "unknown")
            self.assertEqual(analyze_request(case)["decision"], "abstain")

    def test_resource_budget_abstains(self):
        result = analyze_request(packet(), max_assignments=4)
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["candidates"][0]["reason"], "formal_resource_limit")

    def test_strict_structured_output_rejects_extra_and_malformed_fields(self):
        case = packet()
        self.assertEqual(load_structured_case(json.dumps(case)), case)
        altered = deepcopy(case)
        altered["approved"] = True
        with self.assertRaises(ValidationError):
            load_structured_case(altered)
        altered = deepcopy(case)
        altered["candidates"][0]["permissions"][0]["resources"] = ["*"]
        with self.assertRaises(ValidationError):
            validate_case(altered)
        altered = deepcopy(case)
        altered["facts"] = {"approved": 1}
        with self.assertRaises(ValidationError):
            validate_case(altered)
        with self.assertRaises(ValidationError):
            load_structured_case("{bad json}")


class InteractionAndRegressionTests(unittest.TestCase):
    def setUp(self):
        self.case = packet("You may send report to alex or bea once.",
                           operation=request("messages", "send", "report", "alex"))

    def test_instruction_to_question_to_denial_trace(self):
        state = start_session(self.case)
        self.assertEqual(state["result"]["decision"], "ask")
        next_state = step_session(state, {"question": "interpretation", "answer": "c2"})
        self.assertEqual(next_state["result"]["decision"], "deny")
        self.assertEqual(next_state["result"]["active_candidate_ids"], ["c2"])
        self.assertEqual(next_state["result"]["questions_used"], 1)
        self.assertEqual(state["answers"], [])
        self.assertEqual(next_state["case"], state["case"])
        self.assertEqual(next_state["result"]["trace"][1]["before"], ["c1", "c2", "c3"])

    def test_insufficient_and_missing_interpretation_answers_never_grant(self):
        for answer, reason in [("unsure", "insufficient_answer"), ("other", "intention_outside_candidates")]:
            result = analyze_request(self.case, [{"question": "interpretation", "answer": answer}])
            self.assertEqual(result["decision"], "abstain")
            self.assertEqual(result["reason"], reason)
            self.assertEqual(result["active_candidate_ids"], ["c1", "c2", "c3"])

    def test_clarification_cannot_add_grant_or_change_scope(self):
        state = start_session(self.case)
        with self.assertRaises(ValidationError):
            step_session(state, {"question": "interpretation", "answer": "c1", "grant": True})
        expanded = dict(self.case["request"], scope="session")
        with self.assertRaisesRegex(ValidationError, "scope changed"):
            step_session(state, {"question": "interpretation", "answer": "c1"}, expanded)
        altered = deepcopy(state)
        altered["case"]["facts"]["approved"] = True
        with self.assertRaisesRegex(ValidationError, "digest mismatch"):
            step_session(altered, {"question": "interpretation", "answer": "c1"})

    def test_unknown_answer_and_unsolicited_selection_rejected(self):
        for answer in [{"question": "invented", "answer": "c1"}, {"question": "interpretation", "answer": "yes"}]:
            with self.assertRaises(ValidationError):
                analyze_request(self.case, [answer])
        with self.assertRaises(ValidationError):
            analyze_request(packet(), [{"question": "interpretation", "answer": "c1"}])

    def test_zero_question_budget_abstains(self):
        result = analyze_request(self.case, max_questions=0)
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["questions_asked"], 0)

    def test_missing_intention_false_consensus_regression_is_preserved(self):
        # Latent intent is c2 (bea only), which forbids the request to alex.
        # Drop it to reproduce the original project's conceptual failure.
        altered = deepcopy(self.case)
        altered["candidates"] = [candidate for candidate in altered["candidates"] if candidate["id"] != "c2"]
        altered["questions"] = []
        result = analyze_request(altered)
        self.assertEqual(result["decision"], "allow")  # A known false authorization.
        self.assertEqual(result["coverage"], "unverified")
        self.assertIn("conditional_on_coverage", result["reason"])
        self.assertEqual(analyze_request(self.case)["decision"], "ask")

    def test_invalid_question_partition_rejected(self):
        altered = deepcopy(self.case)
        altered["questions"][0]["answers"][1]["retain"] = ["c1"]
        with self.assertRaises(ValidationError):
            analyze_request(altered)

    def test_candidate_and_answer_order_do_not_change_consensus(self):
        altered = deepcopy(self.case)
        altered["candidates"].reverse()
        altered["questions"][0]["answers"].reverse()
        for answer in ["c1", "c2", "c3"]:
            history = [{"question": "interpretation", "answer": answer}]
            self.assertEqual(analyze_request(self.case, history)["decision"], analyze_request(altered, history)["decision"])


class ExhaustivePropertyTests(unittest.TestCase):
    def test_no_allow_without_complete_applicable_grant(self):
        # Exhaust all combinations of the four bounded permission dimensions,
        # expected condition truth, observed truth/unknown, and deny presence.
        for action_ok, resource_ok, scope_ok, expected, actual, prohibited in product(
                [False, True], [False, True], [False, True], [False, True], [None, False, True], [False, True]):
            with self.subTest(values=(action_ok, resource_ok, scope_ok, expected, actual, prohibited)):
                permission = dict(effect="allow", action="read" if action_ok else "write",
                                  resources=["report" if resource_ok else "payroll"], recipients=[None],
                                  scope="session" if scope_ok else "once", conditions={"approved": expected})
                candidate = dict(id="c1", interpretation="bounded property case", permissions=[permission])
                if prohibited:
                    candidate["permissions"].append(dict(effect="deny", action="read", resources=["report"], recipients=[None], scope="once", conditions={}))
                facts = {} if actual is None else {"approved": actual}
                result = evaluate_candidate(request(scope="session"), facts, candidate)
                expected_allow = action_ok and resource_ok and scope_ok and actual is not None and actual == expected and not prohibited
                self.assertEqual(result["decision"] == "allow", expected_allow)

    def test_exhaustive_evaluator_and_direct_boolean_ablation_agree(self):
        for allow_condition, deny_condition in product([None, False, True], repeat=2):
            candidate = dict(id="c1", interpretation="conditional grants", permissions=[
                dict(effect="allow", action="read", resources=["report"], recipients=[None], scope="once", conditions={"a": True}),
                dict(effect="deny", action="read", resources=["report"], recipients=[None], scope="once", conditions={"d": True}),
            ])
            facts = {key: value for key, value in [("a", allow_condition), ("d", deny_condition)] if value is not None}
            checked = evaluate_candidate(request(), facts, candidate)
            direct = evaluate_candidate(request(), facts, candidate, use_verifier=False)
            self.assertEqual(checked["decision"], direct["decision"])

    def test_clarification_only_restricts_existing_candidates(self):
        case = packet("You may read report or payroll once.")
        initial = {candidate["id"] for candidate in case["candidates"]}
        for answer in ["c1", "c2", "c3"]:
            result = analyze_request(case, [{"question": "interpretation", "answer": answer}])
            self.assertLessEqual(set(result["active_candidate_ids"]), initial)
            self.assertEqual(len(result["active_candidate_ids"]), 1)
            self.assertEqual(case, packet("You may read report or payroll once."))


if __name__ == "__main__":
    unittest.main()
