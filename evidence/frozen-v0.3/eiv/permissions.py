"""Bounded simulated authorization, layered on the original finite evaluator.

No function performs an external action. Candidate agreement is conditional on
supplied interpretations, and is never evidence that real intent is covered.
"""

from copy import deepcopy
import hashlib
import itertools
import json
import re

from .logic import ValidationError, analyze_spec

SCHEMA_VERSION = "1.0"
DOMAINS = {"files": {"read", "write", "delete"}, "messages": {"send"}}
SCOPES = {"once", "session"}
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValidationError(f"{label} requires exactly {', '.join(sorted(keys))}")


def _identifier(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(f"{label} must be a bounded identifier")


def _text(value, label, limit=8000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationError(f"{label} must be nonempty text of at most {limit} characters")


def _strings(value, label, nullable=False):
    if not isinstance(value, list) or not 1 <= len(value) <= 16:
        raise ValidationError(f"{label} must have 1-16 entries")
    for item in value:
        if nullable and item is None:
            continue
        _identifier(item, label)
    if len(set(value)) != len(value):
        raise ValidationError(f"{label} entries must be unique")


def validate_request(request):
    _object(request, {"domain", "action", "resource", "recipient", "scope"}, "request")
    if not isinstance(request["domain"], str) or request["domain"] not in DOMAINS or not isinstance(request["action"], str) or request["action"] not in DOMAINS[request["domain"]]:
        raise ValidationError("unsupported domain/action combination")
    _identifier(request["resource"], "resource")
    if request["domain"] == "files":
        if request["recipient"] is not None:
            raise ValidationError("file actions require null recipient")
    else:
        _identifier(request["recipient"], "recipient")
    if not isinstance(request["scope"], str) or request["scope"] not in SCOPES:
        raise ValidationError("scope must be once or session")


def _facts(facts, label="facts"):
    if not isinstance(facts, dict) or len(facts) > 32:
        raise ValidationError(f"{label} must be a map with at most 32 conditions")
    for key, value in facts.items():
        _identifier(key, label)
        if type(value) is not bool:
            raise ValidationError(f"{label} values must be booleans; omit unknown values")


def validate_candidate(candidate, domain):
    _object(candidate, {"id", "interpretation", "permissions"}, "candidate")
    _identifier(candidate["id"], "candidate id")
    _text(candidate["interpretation"], "interpretation")
    if not isinstance(candidate["permissions"], list) or len(candidate["permissions"]) > 16:
        raise ValidationError("permissions must be a list with at most 16 entries")
    for permission in candidate["permissions"]:
        _object(permission, {"effect", "action", "resources", "recipients", "scope", "conditions"}, "permission")
        if not isinstance(permission["effect"], str) or permission["effect"] not in {"allow", "deny"} or not isinstance(permission["action"], str) or permission["action"] not in DOMAINS[domain]:
            raise ValidationError("invalid permission effect or action")
        _strings(permission["resources"], "resources")
        _strings(permission["recipients"], "recipients", nullable=True)
        if domain == "files" and permission["recipients"] != [None]:
            raise ValidationError("file permissions require recipients [null]")
        if domain == "messages" and None in permission["recipients"]:
            raise ValidationError("message permissions require named recipients")
        if not isinstance(permission["scope"], str) or permission["scope"] not in SCOPES:
            raise ValidationError("invalid permission scope")
        _facts(permission["conditions"], "conditions")


def validate_case(case):
    _object(case, {"schema_version", "instruction", "request", "facts", "candidates", "questions", "semantic_status"}, "case")
    if case["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported schema version")
    _text(case["instruction"], "instruction")
    validate_request(case["request"])
    _facts(case["facts"])
    if not isinstance(case["semantic_status"], str) or case["semantic_status"] not in {"controlled", "structured", "unknown"}:
        raise ValidationError("invalid semantic status")
    if not isinstance(case["candidates"], list) or len(case["candidates"]) > 16:
        raise ValidationError("candidates must contain at most 16 entries")
    if not case["candidates"] and case["semantic_status"] != "unknown":
        raise ValidationError("known semantic status requires candidates")
    for candidate in case["candidates"]:
        validate_candidate(candidate, case["request"]["domain"])
    ids = [candidate["id"] for candidate in case["candidates"]]
    if len(set(ids)) != len(ids):
        raise ValidationError("candidate ids must be unique")
    if not isinstance(case["questions"], list) or len(case["questions"]) > 16:
        raise ValidationError("questions must contain at most 16 entries")
    question_ids = []
    for question in case["questions"]:
        _object(question, {"id", "prompt", "answers"}, "question")
        _identifier(question["id"], "question id")
        _text(question["prompt"], "question prompt")
        question_ids.append(question["id"])
        answers = question["answers"]
        if not isinstance(answers, list) or not 2 <= len(answers) <= 16:
            raise ValidationError("question requires 2-16 answers")
        covered, answer_ids = set(), []
        for answer in answers:
            _object(answer, {"id", "label", "retain"}, "answer")
            _identifier(answer["id"], "answer id")
            if answer["id"] in {"other", "unsure"}:
                raise ValidationError("other and unsure are reserved non-selecting answers")
            _text(answer["label"], "answer label")
            _strings(answer["retain"], "retain")
            retained = set(answer["retain"])
            if not retained <= set(ids) or covered & retained:
                raise ValidationError("answers must partition known candidate ids")
            covered |= retained
            answer_ids.append(answer["id"])
        if covered != set(ids) or len(set(answer_ids)) != len(answer_ids):
            raise ValidationError("answers must partition all candidates with unique answer ids")
    if len(set(question_ids)) != len(question_ids):
        raise ValidationError("question ids must be unique")
    return case


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_structured_case(payload):
    """Untrusted future model output uses the same strict validation as fixtures.

    Validation establishes structural validity only, never semantic correctness.
    """
    if isinstance(payload, str):
        if len(payload) > 100000:
            raise ValidationError("structured payload exceeds 100000 characters")
        try:
            payload = json.loads(payload, object_pairs_hook=_unique_json_object)
        except (ValueError, RecursionError) as error:
            raise ValidationError("invalid JSON candidate payload") from error
    validate_case(payload)
    return deepcopy(payload)


def _atom(name):
    return {"atom": {"pred": name, "args": []}}


def _formal_spec(granted, prohibited):
    facts = [{"pred": name, "args": [], "value": value}
             for name, value in (("Granted", granted), ("Prohibited", prohibited))
             if value is not None]
    # The consistency constraint is applied only after unknown inputs are
    # identified by policy; no inferred choice can turn an unknown into consent.
    return {"domain": ["operation"],
            "vocabulary": {"Granted": 0, "Prohibited": 0, "Authorized": 0},
            "facts": facts, "rules": [], "assumptions": [],
            "constraints": [
                {"iff": [_atom("Authorized"), {"and": [_atom("Granted"), {"not": _atom("Prohibited")}]}]},
                {"not": {"and": [_atom("Granted"), _atom("Prohibited")]}}],
            "query": _atom("Authorized")}


def evaluate_candidate(request, facts, candidate, use_verifier=True,
                       max_atoms=12, max_assignments=4096):
    """Check one finite interpretation; no LLM or benchmark labels are read."""
    validate_request(request)
    _facts(facts)
    validate_candidate(candidate, request["domain"])
    if type(use_verifier) is not bool:
        raise ValidationError("use_verifier must be boolean")
    checks = []
    for index, permission in enumerate(candidate["permissions"]):
        dimensions = {
            "action": permission["action"] == request["action"],
            "resource": request["resource"] in permission["resources"],
            "recipient": request["recipient"] in permission["recipients"],
            # A session grant includes a single operation. A prohibition on
            # that operation conflicts with either requested duration.
            "scope": permission["effect"] == "deny" or permission["scope"] == "session" or request["scope"] == "once",
        }
        conditions = {name: (None if name not in facts else facts[name] == expected)
                      for name, expected in permission["conditions"].items()}
        applicable = (False if not all(dimensions.values()) or False in conditions.values()
                      else None if None in conditions.values() else True)
        checks.append({"permission": index, "effect": permission["effect"],
                       "dimensions": dimensions, "conditions": conditions,
                       "applicable": applicable})
    def aggregate(effect):
        values = [check["applicable"] for check in checks if check["effect"] == effect]
        return True if True in values else None if None in values else False
    granted, prohibited = aggregate("allow"), aggregate("deny")
    spec = _formal_spec(granted, prohibited)
    if use_verifier:
        formal = analyze_spec(spec, max_atoms=max_atoms, max_assignments=max_assignments)
    else:
        # A transparent computational ablation, not an intentionally weakened
        # baseline: direct Boolean checking should agree on complete inputs.
        status = ("inconsistent" if granted is True and prohibited is True else
                  "underdetermined" if granted is None or prohibited is None else
                  "entailed" if granted and not prohibited else "refuted")
        formal = {"status": status, "engine": "direct_boolean_ablation", "assignments_examined": 0}
    if formal["status"] == "unknown":
        decision, reason = "abstain", "formal_resource_limit"
    elif formal["status"] == "inconsistent":
        decision, reason = "abstain", "contradictory_permissions"
    elif granted is None or prohibited is None:
        decision, reason = "abstain", "unknown_condition"
    elif formal["status"] == "entailed":
        decision, reason = "allow", "explicit_applicable_permission"
    elif formal["status"] == "refuted":
        decision, reason = "deny", "explicit_prohibition" if prohibited else "no_applicable_permission"
    else:
        decision, reason = "abstain", "formal_underdetermined"
    return {"id": candidate["id"], "decision": decision, "reason": reason,
            "checks": checks, "formal_spec": spec, "formal_result": formal}


def _question(questions, results, active_ids, strategy):
    active = set(active_ids)
    decisions = {row["id"]: row["decision"] for row in results}
    ranked = []
    for order, question in enumerate(questions):
        groups = [set(answer["retain"]) & active for answer in question["answers"]]
        groups = [group for group in groups if group]
        if len(groups) < 2:
            continue
        score = sum(decisions[a] != decisions[b]
                    for i, group in enumerate(groups) for other in groups[i + 1:]
                    for a in group for b in other)
        if score:
            ranked.append((score if strategy == "targeted" else 0, -order, question))
    if not ranked:
        return None
    return deepcopy(max(ranked, key=lambda item: item[:2])[2])


def analyze_request(case, answers=None, max_questions=2, mode="eiv", use_verifier=True,
                    question_strategy="targeted", max_atoms=12, max_assignments=4096):
    """Replay a case and finite clarification history into a simulated decision.

    Answers can only select a displayed partition, never add grants, alter
    facts or change the requested operation. An insufficient/other answer
    terminates with abstention. Re-evaluation requires a new case/session.
    """
    validate_case(case)
    if mode != "eiv":
        raise ValidationError("only eiv mode is supported; baselines belong to the experiment runner")
    if type(max_questions) is not int or not 0 <= max_questions <= 8:
        raise ValidationError("max_questions must be an integer from 0 to 8")
    if not isinstance(question_strategy, str) or question_strategy not in {"targeted", "first"}:
        raise ValidationError("unknown question strategy")
    answers = [] if answers is None else answers
    if not isinstance(answers, list) or len(answers) > max_questions:
        raise ValidationError("clarification history exceeds the interaction budget")
    results = [evaluate_candidate(case["request"], case["facts"], candidate, use_verifier,
                                  max_atoms, max_assignments) for candidate in case["candidates"]]
    active_ids = [candidate["id"] for candidate in case["candidates"]]
    trace = [{"event": "generated", "candidate_ids": active_ids[:],
              "semantic_status": case["semantic_status"], "coverage": "unverified"}]
    answered = 0
    terminal_reason = None
    for step in range(len(answers) + 1):
        statuses = [row["decision"] for row in results if row["id"] in active_ids]
        question = None
        if terminal_reason:
            decision, reason = "abstain", terminal_reason
        elif case["semantic_status"] == "unknown" or not active_ids:
            decision, reason = "abstain", "semantic_generation_unavailable"
        elif all(status == "allow" for status in statuses):
            decision, reason = "allow", "candidate_consensus_conditional_on_coverage"
        elif all(status == "deny" for status in statuses):
            decision, reason = "deny", "candidate_consensus_conditional_on_coverage"
        else:
            question = _question(case["questions"], results, active_ids, question_strategy)
            if question and answered < max_questions:
                decision, reason = "ask", "candidate_decisions_disagree"
            else:
                decision, reason = "abstain", "question_budget_exhausted" if question else "unresolved_interpretation"
                question = None
        if step == len(answers):
            break
        answer = answers[step]
        _object(answer, {"question", "answer"}, "clarification")
        if decision != "ask" or answer["question"] != question["id"]:
            raise ValidationError("clarification must answer the currently suggested question")
        if not isinstance(answer["answer"], str):
            raise ValidationError("answer id must be text")
        answered += 1
        before = active_ids[:]
        if answer["answer"] in {"other", "unsure"}:
            terminal_reason = "intention_outside_candidates" if answer["answer"] == "other" else "insufficient_answer"
        else:
            chosen = next((item for item in question["answers"] if item["id"] == answer["answer"]), None)
            if chosen is None:
                raise ValidationError("unknown clarification answer")
            active_ids = [item for item in active_ids if item in chosen["retain"]]
            if not active_ids:
                terminal_reason = "incompatible_answer"
        trace.append({"event": "clarification", "question": answer["question"], "answer": answer["answer"],
                      "before": before, "after": active_ids[:]})
    for row in results:
        row["active"] = row["id"] in active_ids
    trace.append({"event": "decision", "decision": decision, "reason": reason,
                  "active_candidate_ids": active_ids[:]})
    return {"schema_version": SCHEMA_VERSION, "decision": decision, "reason": reason,
            "suggested_question": question, "candidates": results,
            "active_candidate_ids": active_ids, "coverage": "unverified",
            "scope": "conditional_on_supplied_candidates_formalization_facts_and_bounds",
            "questions_used": answered, "questions_asked": answered + int(decision == "ask"),
            "trace": trace, "simulated": True}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def start_session(case, max_questions=2):
    case = load_structured_case(case)
    return {"schema_version": SCHEMA_VERSION, "case": case, "case_digest": _digest(case),
            "answers": [], "max_questions": max_questions,
            "result": analyze_request(case, max_questions=max_questions)}


def step_session(session, answer, request=None):
    """Return a new state; never mutate an existing session or grant permissions."""
    _object(session, {"schema_version", "case", "case_digest", "answers", "max_questions", "result"}, "session")
    if session["schema_version"] != SCHEMA_VERSION or _digest(session["case"]) != session["case_digest"]:
        raise ValidationError("session version or case digest mismatch")
    if request is not None and request != session["case"]["request"]:
        validate_request(request)
        raise ValidationError("request scope changed; start a new session and revalidate permissions")
    new = deepcopy(session)
    new["answers"].append(deepcopy(answer))
    new["result"] = analyze_request(new["case"], new["answers"], new["max_questions"])
    return new


# Deliberately small, published controlled-language adapter. Unsupported syntax
# fails closed; it is not advertised as an LLM or broad natural-language model.
CLAUSE = re.compile(
    r"^You (?P<modal>may|must not) (?P<action>read|write|delete|send) "
    r"(?P<resources>[A-Za-z][A-Za-z0-9_-]*(?: or [A-Za-z][A-Za-z0-9_-]*)?)"
    r"(?: to (?P<recipients>[A-Za-z][A-Za-z0-9_-]*(?: or [A-Za-z][A-Za-z0-9_-]*)?))? "
    r"(?P<scope>once or for this session|once|for this session)"
    r"(?: (?P<conditional>if|unless) (?P<condition>[A-Za-z][A-Za-z0-9_-]*) is (?P<value>true|false))?$"
)


def _readings(value):
    values = value.split(" or ")
    if len(values) == 1:
        return [(values, values[0])]
    return [([values[0]], values[0] + " only"), ([values[1]], values[1] + " only"),
            (values, "both " + " and ".join(values))]


def parse_instruction(instruction, request, facts):
    """Map documented controlled English to candidate JSON, without labels.

    'or' yields first, second and inclusive interpretations. This is a fixed
    engineering fixture, not a claim that these exhaust human interpretations.
    """
    _text(instruction, "instruction")
    validate_request(request)
    _facts(facts)
    case = {"schema_version": SCHEMA_VERSION, "instruction": instruction,
            "request": deepcopy(request), "facts": deepcopy(facts), "candidates": [],
            "questions": [], "semantic_status": "unknown"}
    parts = instruction.strip().rstrip(".").split(";")
    if not 1 <= len(parts) <= 8:
        return case
    alternatives = []
    for part in parts:
        match = CLAUSE.fullmatch(part.strip())
        if match is None:
            return case
        fields = match.groupdict()
        if fields["action"] not in DOMAINS[request["domain"]]:
            return case
        if (fields["action"] == "send") != bool(fields["recipients"]):
            return case
        resources = _readings(fields["resources"])
        recipients = _readings(fields["recipients"]) if fields["recipients"] else [([None], "no recipient")]
        scopes = [("once", "once"), ("session", "session")] if " or " in fields["scope"] else [("once" if fields["scope"] == "once" else "session", fields["scope"])]
        conditions = {}
        if fields["condition"]:
            expected = fields["value"] == "true"
            conditions[fields["condition"]] = not expected if fields["conditional"] == "unless" else expected
        readings = []
        for (resource, rlabel), (recipient, tlabel), (scope, slabel) in itertools.product(resources, recipients, scopes):
            permission = {"effect": "allow" if fields["modal"] == "may" else "deny", "action": fields["action"],
                          "resources": resource, "recipients": recipient, "scope": scope, "conditions": conditions}
            readings.append((permission, f"{permission['effect']} {fields['action']} {rlabel}; recipient {tlabel}; scope {slabel}"))
        alternatives.append(readings)
    count = 1
    for items in alternatives:
        count *= len(items)
    if count > 16:
        return case
    for index, combination in enumerate(itertools.product(*alternatives), 1):
        case["candidates"].append({"id": f"c{index}", "interpretation": " / ".join(item[1] for item in combination),
                                    "permissions": [deepcopy(item[0]) for item in combination]})
    case["semantic_status"] = "controlled"
    if len(case["candidates"]) > 1:
        case["questions"] = [{"id": "interpretation", "prompt": "Which permission interpretation matches your intent? You may answer other or unsure.",
                              "answers": [{"id": candidate["id"], "label": candidate["interpretation"], "retain": [candidate["id"]]}
                                          for candidate in case["candidates"]]}]
    try:
        return validate_case(case)
    except ValidationError:
        case["candidates"] = []
        case["questions"] = []
        case["semantic_status"] = "unknown"
        return case
