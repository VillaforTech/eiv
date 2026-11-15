"""Exact, bounded clarification planning over a supplied finite candidate set.

The objective is lexicographic: maximize the number of candidate hypotheses
resolved as unanimous allow/deny within the remaining question budget, then
minimize the sum of questions over those hypotheses (including unresolved ones),
then prefer the earliest input question. Each candidate has weight one. These
counts are not probabilities of human intention or a claim of semantic coverage.

Questions must partition the supplied candidates. The calculation assumes
truthful selecting answers; an ``other`` or ``unsure`` response must still cause
the caller to abstain. No latent intent, benchmark label, or external tool is
consulted. Resource exhaustion raises instead of returning an approximate plan.
"""

from copy import deepcopy
from functools import lru_cache
import re

from .logic import ValidationError


class PlanningLimitError(ValidationError):
    """The exact calculation exceeded its explicitly bounded work allowance."""


_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_DECISIONS = {"allow", "deny", "abstain"}


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _text(value):
    return isinstance(value, str) and 0 < len(value) <= 8000 and bool(value.strip())


def _validate(questions, results, active_ids, remaining_budget,
              max_states, max_transitions):
    if type(remaining_budget) is not int or not 0 <= remaining_budget <= 8:
        raise ValidationError("remaining_budget must be an integer from 0 to 8")
    for name, value in (("max_states", max_states), ("max_transitions", max_transitions)):
        if type(value) is not int or not 1 <= value <= 1000000:
            raise ValidationError(name + " must be an integer from 1 to 1000000")
    if not isinstance(results, list) or len(results) > 16:
        raise ValidationError("planner results must contain at most 16 candidates")
    ids = []
    for row in results:
        if (not isinstance(row, dict) or not _identifier(row.get("id"))
                or not isinstance(row.get("decision"), str)
                or row["decision"] not in _DECISIONS):
            raise ValidationError("planner results need a candidate id and finite decision")
        ids.append(row["id"])
    if len(set(ids)) != len(ids):
        raise ValidationError("planner candidate ids must be unique")
    if (not isinstance(active_ids, list) or len(active_ids) > 16
            or any(not _identifier(cid) for cid in active_ids)
            or len(set(active_ids)) != len(active_ids)
            or not set(active_ids) <= set(ids)):
        raise ValidationError("active_ids must be a unique subset of planner candidate ids")
    if not isinstance(questions, list) or len(questions) > 16:
        raise ValidationError("planner questions must contain at most 16 entries")
    question_ids = set()
    for question in questions:
        if (not isinstance(question, dict)
                or set(question) != {"id", "prompt", "answers"}
                or not _identifier(question.get("id"))
                or not _text(question.get("prompt"))):
            raise ValidationError("planner question requires id, prompt and answers")
        if question["id"] in question_ids:
            raise ValidationError("planner question ids must be unique")
        question_ids.add(question["id"])
        answers = question["answers"]
        if not isinstance(answers, list) or not 2 <= len(answers) <= 16:
            raise ValidationError("planner question requires 2-16 answers")
        covered, answer_ids = set(), set()
        for answer in answers:
            if (not isinstance(answer, dict)
                    or set(answer) != {"id", "label", "retain"}
                    or not _identifier(answer.get("id"))
                    or answer["id"] in {"other", "unsure"}
                    or answer["id"] in answer_ids
                    or not _text(answer.get("label"))):
                raise ValidationError("planner answers need unique selecting ids and labels")
            answer_ids.add(answer["id"])
            retain = answer["retain"]
            if (not isinstance(retain, list) or not 1 <= len(retain) <= 16
                    or any(not _identifier(cid) for cid in retain)
                    or len(set(retain)) != len(retain)):
                raise ValidationError("planner retain must contain unique candidate ids")
            retained = set(retain)
            if not retained <= set(ids) or covered & retained:
                raise ValidationError("planner answers must partition candidate ids")
            covered |= retained
        if covered != set(ids):
            raise ValidationError("planner answers must partition all candidate ids")


def plan_questions(questions, results, active_ids, remaining_budget, *,
                   max_states=20000, max_transitions=200000):
    """Return an exact finite plan's first question and auditable objective counts.

    An unresolved branch may stop without asking. Thus a question with no
    eventual resolution benefit is not selected merely to consume the budget.
    Previously answered questions need no separate history: after restriction
    they have only one nonempty branch and cannot be selected again.

    ``total_questions`` sums question counts along every active candidate's
    truthful path, including paths ending in abstention. ``resolved_candidates``
    counts candidates reaching a unanimous allow/deny leaf. The caller remains
    responsible for evaluating permissions and honoring nonselecting answers.
    """
    _validate(questions, results, active_ids, remaining_budget,
              max_states, max_transitions)
    # Candidate masks make the memoization key independent of answer order.
    bits = {row["id"]: 1 << index for index, row in enumerate(results)}
    active = sum(bits[cid] for cid in active_ids)
    allow = sum(bits[row["id"]] for row in results if row["decision"] == "allow")
    deny = sum(bits[row["id"]] for row in results if row["decision"] == "deny")
    partitions = [tuple(sum(bits[cid] for cid in answer["retain"])
                        for answer in question["answers"])
                  for question in questions]
    work = {"states": 0, "transitions": 0}

    @lru_cache(maxsize=None)
    def solve(mask, budget):
        work["states"] += 1
        if work["states"] > max_states:
            raise PlanningLimitError("exact planner state limit exceeded")
        count = mask.bit_count()
        if mask and (mask & allow == mask or mask & deny == mask):
            return count, 0, None
        if not mask or budget == 0:
            return 0, 0, None
        # Stopping is always legal. Only a strict lexicographic improvement
        # replaces it, so all-zero-gain questions are rejected.
        best = (0, 0, None)
        for index, partition in enumerate(partitions):
            work["transitions"] += 1
            if work["transitions"] > max_transitions:
                raise PlanningLimitError("exact planner transition limit exceeded")
            groups = tuple(group & mask for group in partition if group & mask)
            if len(groups) < 2:
                continue
            children = [solve(group, budget - 1) for group in groups]
            resolved = sum(child[0] for child in children)
            questions_total = count + sum(child[1] for child in children)
            if (resolved, -questions_total) > (best[0], -best[1]):
                best = (resolved, questions_total, index)
        return best

    resolved, total_questions, index = solve(active, remaining_budget)
    return {
        "suggested_question": deepcopy(questions[index]) if index is not None else None,
        "resolved_candidates": resolved,
        "candidate_count": len(active_ids),
        "total_questions": total_questions,
        "remaining_budget": remaining_budget,
        "states_evaluated": work["states"],
        "transitions_evaluated": work["transitions"],
        "objective": "maximize_resolved_candidates_then_minimize_total_questions",
        "candidate_weighting": "equal_counts_not_intent_probabilities",
        "answer_assumption": "truthful_selecting_partition_answers",
        "coverage": "unverified",
        "exact": True,
    }


def select_question(questions, results, active_ids, remaining_budget, *,
                    max_states=20000, max_transitions=200000):
    """Return the exact plan's first question, or None when stopping is optimal."""
    return plan_questions(questions, results, active_ids, remaining_budget,
                          max_states=max_states,
                          max_transitions=max_transitions)["suggested_question"]
