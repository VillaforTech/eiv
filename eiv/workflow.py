"""Candidate interpretation handling and explicit clarification."""

from .logic import ValidationError, analyze_spec


def _validate_case(case):
    if not isinstance(case, dict) or not {"title", "source_type", "candidates", "questions"} <= set(case):
        raise ValidationError("case requires title, source_type, candidates, questions")
    if case["source_type"] not in ("manually_formalized_fixture", "manual_formalization"):
        raise ValidationError("this prototype accepts only manual formalizations, not unreviewed adapter proposals")
    candidates = case["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValidationError("case requires at least one candidate")
    ids = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != {"id", "interpretation", "spec"}:
            raise ValidationError("candidate requires id, interpretation, spec")
        if not all(isinstance(candidate[key], str) and candidate[key] for key in ("id", "interpretation")):
            raise ValidationError("candidate id and interpretation must be nonempty strings")
        ids.append(candidate["id"])
    if len(ids) != len(set(ids)):
        raise ValidationError("candidate ids must be unique")
    questions = case["questions"]
    if not isinstance(questions, list):
        raise ValidationError("questions must be a list")
    question_ids = []
    for question in questions:
        if not isinstance(question, dict) or set(question) != {"id", "prompt", "answers"}:
            raise ValidationError("question requires id, prompt, answers")
        if not isinstance(question["id"], str) or not isinstance(question["prompt"], str):
            raise ValidationError("question id and prompt must be strings")
        question_ids.append(question["id"])
        answers = question["answers"]
        if not isinstance(answers, list) or len(answers) < 2:
            raise ValidationError("question requires at least two answers")
        answer_ids, seen = [], set()
        for answer in answers:
            if not isinstance(answer, dict) or set(answer) != {"id", "label", "retain"}:
                raise ValidationError("answer requires id, label, retain")
            if not isinstance(answer["id"], str) or not isinstance(answer["label"], str):
                raise ValidationError("answer id and label must be strings")
            answer_ids.append(answer["id"])
            retain = answer["retain"]
            if not isinstance(retain, list) or not retain or not all(isinstance(x, str) for x in retain):
                raise ValidationError("retain must be a nonempty set of candidate ids")
            if len(retain) != len(set(retain)):
                raise ValidationError("retain must not repeat candidate ids")
            if not set(retain) <= set(ids) or seen & set(retain):
                raise ValidationError("question answers must partition known candidates")
            seen.update(retain)
        if len(answer_ids) != len(set(answer_ids)) or seen != set(ids):
            raise ValidationError("question answers must partition every candidate")
    if len(question_ids) != len(set(question_ids)):
        raise ValidationError("question ids must be unique")


def _distinguishing_question(questions, active_ids):
    active = set(active_ids)
    for question in questions:
        groups = [active & set(answer["retain"]) for answer in question["answers"]]
        if sum(bool(group) for group in groups) >= 2:
            return question
    return None


def analyze_case(case, clarification=None, max_atoms=12, max_assignments=4096):
    """Evaluate every candidate; never silently discard an inconsistent one.

    A clarification must name a predeclared question and answer. Its partition
    is applied before aggregation and is reported as an explicit exclusion.
    """
    _validate_case(case)
    all_ids = [candidate["id"] for candidate in case["candidates"]]
    active_ids = list(all_ids)
    clarification_record = None
    exclusions = []
    if clarification is not None:
        if not isinstance(clarification, dict) or set(clarification) != {"question", "answer"}:
            raise ValidationError("clarification requires question and answer")
        question = next((q for q in case["questions"] if q["id"] == clarification["question"]), None)
        if question is None:
            raise ValidationError("unknown clarification question")
        answer = next((a for a in question["answers"] if a["id"] == clarification["answer"]), None)
        if answer is None:
            raise ValidationError("unknown clarification answer")
        active_ids = [candidate_id for candidate_id in all_ids if candidate_id in answer["retain"]]
        exclusions = [{"candidate": candidate_id, "reason": f"user selected {question['id']}={answer['id']}"}
                      for candidate_id in all_ids if candidate_id not in active_ids]
        clarification_record = {"question": question["id"], "answer": answer["id"],
                                "before": all_ids, "after": active_ids}
    results = []
    for candidate in case["candidates"]:
        result = analyze_spec(candidate["spec"], max_atoms, max_assignments)
        results.append({"id": candidate["id"], "interpretation": candidate["interpretation"],
                        "active": candidate["id"] in active_ids, "result": result})
    statuses = [row["result"]["status"] for row in results if row["active"]]
    question = _distinguishing_question(case["questions"], active_ids)
    if "inconsistent" in statuses:
        action, answer, reason = ("ask" if question else "blocked_inconsistent", None,
                                  "At least one active candidate has no model; it remains visible and blocks a truth answer.")
    elif "unknown" in statuses:
        action, answer, reason = ("blocked_unknown", None,
                                  "At least one active candidate exceeded the finite evaluation budget.")
    elif all(status == "entailed" for status in statuses):
        action, answer, reason = "answer", "yes", "The query holds in every model of every active candidate."
    elif all(status == "refuted" for status in statuses):
        action, answer, reason = "answer", "no", "The query fails in every model of every active candidate."
    elif all(status == "underdetermined" for status in statuses):
        action, answer, reason = "underdetermined", None, "Every active candidate has a witness and a countermodel."
    elif question:
        action, answer, reason = "ask", None, "Active candidates do not justify the same truth answer."
    else:
        action, answer, reason = "blocked_ambiguity", None, "Active candidates disagree and no separating question is supplied."
    return {"title": case["title"], "source_type": case["source_type"],
            "action": action, "answer": answer, "reason": reason,
            "scope": "conditional_on_supplied_candidates_and_formalizations",
            "candidate_coverage": "unverified", "clarification": clarification_record,
            "excluded_candidates": exclusions, "candidates": results,
            "suggested_question": question if action == "ask" else None}
