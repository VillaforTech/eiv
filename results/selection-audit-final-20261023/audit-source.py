"""Post-v3 independent evidence audit and a finite greedy-selection counterexample.

Does not edit frozen sources, rerun inference, or execute a requested operation.
Saved outcome checks use a separate operation-membership interpretation and
independent aggregation. Only the new counterexample invokes the real core.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
V2_ARMS = ("direct", "conventional", "eiv", "eiv_no_exhaustive_verifier", "eiv_first_candidate", "eiv_first_question")
V3_ARMS = ("direct", "ordinary_first", "fixed_order", "eiv_targeted", "abstain_all")
BUDGETS = (0, 1, 2, 3)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def operation_membership(request, facts, candidate):
    """Independent denotation via explicit concrete operation sets.

    Matches the published permission contract, including conservative unknown
    conditions. Does not use the parser, dimension checker, compiler or solver.
    """
    operation = (request["action"], request["resource"], request["recipient"], request["scope"])
    applicable = {"allow": set(), "deny": set()}
    for permission in candidate["permissions"]:
        scopes = ("once", "session") if permission["effect"] == "deny" or permission["scope"] == "session" else ("once",)
        relation = set(itertools.product([permission["action"]], permission["resources"], permission["recipients"], scopes))
        conditions = permission["conditions"]
        if operation not in relation or any(name in facts and facts[name] != value for name, value in conditions.items()):
            continue
        applicable[permission["effect"]].add("unknown" if any(name not in facts for name in conditions) else "known")
    grant = "known" in applicable["allow"]
    prohibition = "known" in applicable["deny"]
    if grant and prohibition:
        return "abstain"
    if any("unknown" in applicable[effect] and "known" not in applicable[effect] for effect in applicable):
        return "abstain"
    return "allow" if grant and not prohibition else "deny"


def policy_key(candidate):
    permissions = []
    for item in candidate["permissions"]:
        item = deepcopy(item)
        item["resources"].sort()
        item["recipients"].sort(key=lambda value: "" if value is None else value)
        permissions.append(json.dumps(item, sort_keys=True))
    return sorted(permissions)


def independent_metrics(rows, label_key):
    n = len(rows)
    denials = sum(row[label_key] == "deny" for row in rows)
    permissions = sum(row[label_key] == "allow" for row in rows)
    false_allow = sum(row["decision"] == "allow" and row[label_key] == "deny" for row in rows)
    false_deny = sum(row["decision"] == "deny" and row[label_key] == "allow" for row in rows)
    correct = sum(row["decision"] == row[label_key] for row in rows)
    abstain = sum(row["decision"] == "abstain" for row in rows)
    divide = lambda a, b: a / b if b else None
    return {"n": n, "latent_deny_n": denials, "latent_allow_n": permissions,
            "false_authorization_n": false_allow, "false_authorization_rate": divide(false_allow, denials),
            "false_denial_n": false_deny, "false_denial_rate": divide(false_deny, permissions),
            "correct_resolved_n": correct, "correct_resolved_rate": divide(correct, n),
            "abstention_n": abstain, "abstention_rate": divide(abstain, n),
            "resolved_n": n - abstain, "selective_accuracy": divide(correct, n - abstain),
            "questions_total": sum(row["questions"] for row in rows),
            "questions_mean": divide(sum(row["questions"] for row in rows), n)}


def verify_common_metrics(rows, saved, label_key):
    recomputed = independent_metrics(rows, label_key)
    for key, value in recomputed.items():
        require(saved.get(key) == value, "metric mismatch: " + key)
    return recomputed


def verify_outcome_flags(row, label_key):
    require(row["decision"] in {"allow", "deny", "abstain"}, "invalid final decision")
    expected = {"correct_resolved": row["decision"] == row[label_key],
                "false_authorization": row["decision"] == "allow" and row[label_key] == "deny",
                "false_denial": row["decision"] == "deny" and row[label_key] == "allow"}
    require(all(type(row[key]) is bool and row[key] == value for key, value in expected.items()), "outcome flag mismatch")


def audit_v2(cases, rows, saved):
    by_id = {case["case_id"]: case for case in cases if case["split"] == "test"}
    required = set(itertools.product(by_id, V2_ARMS))
    observed = [(row["case_id"], row["arm"]) for row in rows]
    require(len(observed) == len(set(observed)) and set(observed) == required, "v2 missing, duplicate or extra case/arm record")
    # Check every label, including development/validation, without the core.
    for case in cases:
        expected = operation_membership(case["request"], case["latent_facts"], case["latent_intent"]["candidate"])
        require(case["expected_decision"] == expected, "v2 label disagrees with denotation: " + case["case_id"])
    formal_checks = 0
    for row in rows:
        case = by_id[row["case_id"]]
        require(row["expected_decision"] == case["expected_decision"] and row["family"] == case["family"], "v2 metadata/label mismatch")
        verify_outcome_flags(row, "expected_decision")
        public = row["generated_case"]
        policies = {candidate["id"]: candidate for candidate in public["candidates"]}
        for result in row["formal_outputs"]:
            expected = operation_membership(public["request"], public["facts"], policies[result["id"]])
            require(result["decision"] == expected, "v2 finite candidate decision mismatch")
            formal_checks += 1
        intended = policy_key(case["latent_intent"]["candidate"])
        covered = any(policy_key(candidate) == intended for candidate in policies.values())
        require(row["initial_candidate_coverage"] == covered, "v2 initial coverage mismatch")
        final_ids = set()
        for event in row["trace"]:
            if event.get("event") == "decision":
                final_ids = set(event.get("active_candidate_ids", []))
        final_coverage = any(cid in final_ids and policy_key(candidate) == intended for cid, candidate in policies.items())
        require(row["final_candidate_coverage"] == final_coverage, "v2 retained coverage mismatch")
    for arm in V2_ARMS:
        group = [row for row in rows if row["arm"] == arm]
        metrics = saved["metrics"][arm]
        verify_common_metrics(group, metrics, "expected_decision")
        extra = {"resolution_rate": sum(row["decision"] != "abstain" for row in group) / len(group),
                 "questions_distribution": dict(Counter(str(row["questions"]) for row in group)),
                 "initial_candidate_coverage_n": sum(row["initial_candidate_coverage"] for row in group),
                 "final_candidate_coverage_rate_all": sum(row["final_candidate_coverage"] for row in group) / len(group),
                 "initial_candidate_coverage_rate_all": sum(row["initial_candidate_coverage"] for row in group) / len(group),
                 "initial_candidate_coverage_rate_generated": sum(row["initial_candidate_coverage"] for row in group) / sum(row["initial_candidate_count"] > 0 for row in group),
                 "generated_candidate_cases_n": sum(row["initial_candidate_count"] > 0 for row in group),
                 "latency_seconds_median": statistics.median(row["latency_seconds"] for row in group),
                 "latency_seconds_p90": sorted(row["latency_seconds"] for row in group)[math.ceil(.9 * len(group)) - 1],
                 "external_monetary_cost_usd": sum(row["monetary_cost_usd"] for row in group)}
        extra.update({key: sum(row["usage"][source] for row in group) for key, source in
                      [("model_calls", "calls"), ("input_tokens", "input_tokens"), ("output_tokens", "output_tokens")]})
        require(all(metrics[key] == value for key, value in extra.items()), "v2 additional metric mismatch")
    for family, arms in saved["per_family"].items():
        for arm, metrics in arms.items():
            verify_common_metrics([row for row in rows if row["family"] == family and row["arm"] == arm], metrics, "expected_decision")
    # Recompute every saved paired point and descriptive cluster interval.
    by_arm = {arm: {row["case_id"]: row for row in rows if row["arm"] == arm} for arm in V2_ARMS}
    families = sorted({case["family"] for case in by_id.values()})
    by_family = {family: [cid for cid in by_arm["eiv"] if by_id[cid]["family"] == family] for family in families}
    def differences(ids, comparator):
        left = independent_metrics([by_arm["eiv"][cid] for cid in ids], "expected_decision")
        right = independent_metrics([by_arm[comparator][cid] for cid in ids], "expected_decision")
        return {key: left[key] - right[key] if left[key] is not None and right[key] is not None else None for key in
                ("false_authorization_rate", "correct_resolved_rate", "abstention_rate", "questions_mean")}
    for paired in saved["paired"]:
        comparator = paired["comparator"]
        require(paired["point"] == differences(list(by_arm["eiv"]), comparator), "v2 paired point mismatch")
        require(paired["family_n"] == len(families), "v2 bootstrap family count mismatch")
        rng = random.Random(paired["seed"])
        samples = {key: [] for key in paired["point"]}
        for _ in range(paired["resamples"]):
            ids = [cid for family in rng.choices(families, k=len(families)) for cid in by_family[family]]
            for key, value in differences(ids, comparator).items():
                if value is not None:
                    samples[key].append(value)
        interval = {}
        for key, values in samples.items():
            values.sort()
            interval[key] = [values[int(.025 * (len(values) - 1))], values[int(.975 * (len(values) - 1))]]
        require(interval == paired["family_bootstrap_95_percentile"], "v2 descriptive interval mismatch")
    return {"labels_checked": len(cases), "records_checked": len(rows), "case_arm_pairs_complete": True,
            "candidate_decisions_independently_checked": formal_checks,
            "aggregate_and_family_outcomes": "matched", "paired_points_and_descriptive_intervals": "matched",
            "boundary": "Independent code within the same AI-assisted project; no independent human label review."}


def question_scores(public, decisions, active):
    scores = []
    for question in public["questions"]:
        groups = [set(answer["retain"]) & set(active) for answer in question["answers"]]
        groups = [group for group in groups if group]
        if len(groups) < 2:
            continue
        group_of = {cid: index for index, group in enumerate(groups) for cid in group}
        score = sum(decisions[left] != decisions[right] and group_of[left] != group_of[right]
                    for left, right in itertools.combinations(active, 2))
        scores.append((question, score))
    return scores


def reference_policy(case, arm, budget, decisions):
    """Separate finite-set replay; no production selector or run_one calls."""
    public = case["public"]
    active = [candidate["id"] for candidate in public["candidates"]]
    history, trace = [], []
    while True:
        statuses = {decisions[cid] for cid in active}
        if arm == "abstain_all":
            decision, reason = "abstain", "abstain_all_control"
        elif len(statuses) == 1 and statuses <= {"allow", "deny"}:
            decision, reason = next(iter(statuses)), "candidate_consensus_conditional_on_coverage"
        elif arm == "direct":
            decision, reason = "abstain", "no_clarification_control"
        else:
            available = question_scores(public, decisions, active)
            if arm != "fixed_order":
                available = [(question, score) for question, score in available if score > 0]
            if not available:
                decision, reason = "abstain", "unresolved_interpretation"
            elif len(history) == budget:
                decision, reason = "abstain", "question_budget_exhausted"
            else:
                question, score = max(available, key=lambda pair: pair[1]) if arm == "eiv_targeted" else available[0]
                answer = case["oracle"]["behavior"]
                if answer == "truthful":
                    answer = "v" + str(case["oracle"]["dimensions"][int(question["id"][1:])])
                history.append({"question": question["id"], "answer": answer})
                retained = active[:] if answer in {"other", "unsure"} else [cid for cid in active if cid in next(a for a in question["answers"] if a["id"] == answer)["retain"]]
                trace.append({"question": question["id"], "answer": answer, "before": active[:], "after": retained,
                              "separated_decision_pairs": score})
                active = retained
                if answer in {"other", "unsure"}:
                    decision, reason = "abstain", "intention_outside_candidates" if answer == "other" else "insufficient_answer"
                else:
                    continue
        return {"decision": decision, "reason": reason, "active_candidate_ids": active,
                "oracle_access": history, "trace": trace, "questions": len(history)}


def audit_v3(cases, rows, saved):
    by_id = {case["case_id"]: case for case in cases}
    required = set(itertools.product(by_id, V3_ARMS, BUDGETS))
    observed = [(row["case_id"], row["arm"], row["budget"]) for row in rows]
    require(len(by_id) == len(cases), "v3 duplicate input case")
    require(len(observed) == len(set(observed)) and set(observed) == required, "v3 missing, duplicate or extra outcome")
    complete = {}
    checks_by_case = {}
    candidate_checks = 0
    for case in cases:
        public = case["public"]
        checks_by_case[case["case_id"]] = {candidate["id"]: operation_membership(public["request"], public["facts"], candidate) for candidate in public["candidates"]}
        candidate_checks += len(public["candidates"])
        if case["condition"] == "complete":
            for candidate in public["candidates"]:
                complete[(case["family"], candidate["id"])] = candidate
    for case in cases:
        latent = complete[(case["family"], case["oracle"]["latent_candidate_id"])]
        require(operation_membership(case["public"]["request"], case["public"]["facts"], latent) == case["gold_decision"], "v3 gold contradicts independent policy denotation")
    for row in rows:
        case = by_id[row["case_id"]]
        require(row["gold_decision"] == case["gold_decision"] and row["condition"] == case["condition"] and row["family"] == case["family"], "v3 label/condition metadata mismatch")
        require(row["question_order"] == case["question_order"] and row["primary_question_position"] == case["question_order"].index(0) + 1, "v3 question position mismatch")
        verify_outcome_flags(row, "gold_decision")
        reference = reference_policy(case, row["arm"], row["budget"], checks_by_case[row["case_id"]])
        require(all(row[key] == value for key, value in reference.items()), "v3 independent policy replay mismatch: " + row["case_id"])
        candidate_ids = checks_by_case[row["case_id"]]
        expected_coverage = case["oracle"]["latent_candidate_id"] in candidate_ids
        require(row["initial_candidate_coverage"] == expected_coverage == case["initial_candidate_coverage"], "v3 initial coverage mismatch")
        require(row["retained_candidate_coverage"] == (case["oracle"]["latent_candidate_id"] in row["active_candidate_ids"]), "v3 retained coverage mismatch")
        require(row["candidate_count"] == len(candidate_ids) and row["simulated"] is True, "v3 candidate count/simulation mismatch")
        require(row["formal_statuses"] == {cid: "entailed" if decision == "allow" else "refuted" for cid, decision in candidate_ids.items()}, "v3 finite status mismatch")
        normal = sum(answer["answer"] not in {"other", "unsure"} for answer in reference["oracle_access"])
        require(row["dimension_answer_disclosures"] == normal and row["nonselecting_replies"] == row["questions"] - normal, "v3 disclosure count mismatch")
    def check_group(group, metrics):
        verify_common_metrics(group, metrics, "gold_decision")
        for key in ("dimension_answer_disclosures", "nonselecting_replies", "initial_candidate_coverage_n", "retained_candidate_coverage_n"):
            source = key.removesuffix("_n")
            require(metrics[key] == sum(row[source] for row in group), "v3 additional metric mismatch: " + key)
        require(metrics["questions_distribution"] == {str(budget): sum(row["questions"] == budget for row in group) for budget in BUDGETS}, "v3 question distribution mismatch")
    for budget, arms in saved["metrics_by_budget"].items():
        for arm, metrics in arms.items():
            check_group([row for row in rows if row["budget"] == int(budget) and row["arm"] == arm], metrics)
    for group_name, field in [("by_condition", "condition"), ("by_family", "family"), ("by_primary_question_position", "primary_question_position")]:
        for value, budgets in saved[group_name].items():
            for budget, arms in budgets.items():
                for arm, metrics in arms.items():
                    check_group([row for row in rows if str(row[field]) == value and row["budget"] == int(budget) and row["arm"] == arm], metrics)
    require(saved["records"] == len(rows) and saved["case_count"] == len(cases), "v3 summary completeness mismatch")
    return {"labels_checked": len(cases), "records_checked": len(rows), "candidate_decisions_independently_checked": candidate_checks,
            "complete_case_arm_budget_product": True, "all_saved_trace_and_answer_fields": "matched independent replay",
            "all_aggregate_and_stratified_metrics": "matched", "boundary": "Known finite dataset audited within the same project; not independent human evidence."}


def counterexample_case():
    candidates = []
    for index in range(1, 9):
        candidates.append({"id": "k" + str(index), "interpretation": "Constructed policy " + str(index),
                           "permissions": [{"effect": "allow", "action": "read", "resources": ["report" if index <= 4 else "unrelated"],
                                            "recipients": [None], "scope": "once", "conditions": {}},
                                           {"effect": "allow", "action": "write", "resources": ["record" + str(index)],
                                            "recipients": [None], "scope": "once", "conditions": {}}]})
    ids = [candidate["id"] for candidate in candidates]
    return {"schema_version": "1.0", "semantic_status": "structured",
            "instruction": "Authored finite policy alternatives. Each clarification reveals only membership in its displayed partition.",
            "request": {"domain": "files", "action": "read", "resource": "report", "recipient": None, "scope": "once"},
            "facts": {}, "candidates": candidates,
            "questions": [
                {"id": "isolate", "prompt": "Is the intended policy k8 or one of the other seven listed policies?",
                 "answers": [{"id": "rest", "label": "One of the other seven", "retain": ids[:-1]}, {"id": "last", "label": "k8", "retain": ids[-1:]}]},
                {"id": "balanced", "prompt": "Which of these two listed policy groups contains the intended policy?",
                 "answers": [{"id": "left", "label": "k1, k2, k5 or k6", "retain": ["k1", "k2", "k5", "k6"]},
                             {"id": "right", "label": "k3, k4, k7 or k8", "retain": ["k3", "k4", "k7", "k8"]}]}]}


def run_counterexample():
    from eiv.permissions import analyze_request, validate_case
    case = counterexample_case()
    validate_case(case)
    decisions = {candidate["id"]: operation_membership(case["request"], case["facts"], candidate) for candidate in case["candidates"]}
    scores = dict((question["id"], score) for question, score in question_scores(case, decisions, list(decisions)))
    one_step = []
    for question in case["questions"]:
        resolved = sum(len(answer["retain"]) for answer in question["answers"]
                       if len({decisions[cid] for cid in answer["retain"]}) == 1)
        one_step.append({"question": question["id"], "separated_unlike_pairs": scores[question["id"]],
                         "immediately_resolved_candidates": resolved,
                         "candidate_denominator": len(decisions)})
    one_step_choice = max(one_step, key=lambda row: row["immediately_resolved_candidates"])["question"]
    require(one_step_choice == "isolate", "one-step resolution comparator changed")
    rows = []
    for budget, strategy, intended in itertools.product((0, 1, 2), ("targeted", "first"), decisions):
        answers = []
        result = analyze_request(case, max_questions=budget, question_strategy=strategy)
        while result["decision"] == "ask":
            question = result["suggested_question"]
            answer = next(answer for answer in question["answers"] if intended in answer["retain"])
            answers.append({"question": question["id"], "answer": answer["id"]})
            result = analyze_request(case, answers, max_questions=budget, question_strategy=strategy)
        active_decisions = {decisions[cid] for cid in result["active_candidate_ids"]}
        expected = next(iter(active_decisions)) if len(active_decisions) == 1 else "abstain"
        require(result["decision"] == expected, "counterexample core differs from independent terminal denotation")
        require(all(row["decision"] == decisions[row["id"]] for row in result["candidates"]), "counterexample candidate core differs from independent denotation")
        rows.append({"budget": budget, "arm": strategy, "latent_candidate": intended, "gold_decision": decisions[intended],
                     "decision": result["decision"], "questions": result["questions_used"], "answers": answers,
                     "expected_terminal_decision": expected, "active_candidate_ids": result["active_candidate_ids"], "trace": result["trace"]})
    metrics = {str(budget): {strategy: independent_metrics([row for row in rows if row["budget"] == budget and row["arm"] == strategy], "gold_decision")
                            for strategy in ("targeted", "first")} for budget in (0, 1, 2)}
    required = {"0": (0, 0, 0, 0), "1": (0, 1, 8, 8), "2": (1, 1, 12, 15)}
    for budget, counts in required.items():
        actual = (metrics[budget]["targeted"]["correct_resolved_n"], metrics[budget]["first"]["correct_resolved_n"],
                  metrics[budget]["targeted"]["questions_total"], metrics[budget]["first"]["questions_total"])
        require(actual == counts, "counterexample result changed from explicitly predicted counts")
    terminal_checks = []
    for strategy, budget, answer in itertools.product(("targeted", "first"), (1, 2), ("other", "unsure")):
        initial = analyze_request(case, max_questions=budget, question_strategy=strategy)
        result = analyze_request(case, [{"question": initial["suggested_question"]["id"], "answer": answer}], max_questions=budget, question_strategy=strategy)
        require(result["decision"] == "abstain" and result["questions_used"] == 1, "counterexample nonselecting answer did not abstain")
        terminal_checks.append({"arm": strategy, "budget": budget, "answer": answer, "decision": result["decision"]})
    return case, rows, {"kind": "post_v3_constructive_counterexample_not_new_population_study",
                        "candidate_count": 8, "latent_allow_n": 4, "latent_deny_n": 4, "question_scores": scores,
                        "root_question_diagnostics": one_step, "one_step_resolution_choice": one_step_choice,
                        "one_step_resolution_boundary": "Uses only public partitions and finite consequences. Counts candidate possibilities equally; does not infer a prior over people. It coincides with the evaluated first comparator in this example and is not asserted globally optimal.",
                        "counts_by_budget": metrics, "other_unsure_checks": terminal_checks,
                        "interpretation": "At budget one the core's strict maximum pair-separation score resolves 0/8 candidate intentions; first isolates k8 and resolves 1/8. Equal weighting is finite enumeration, not a prior over human intention. Neither policy is claimed generally optimal."}


def markdown(audit, counter):
    lines = ["# Post-v3 independent evidence and selection audit", "", "This is a post-exposure, AI-assisted engineering audit. No frozen v2/v3 inputs, source or results were changed. It supplies no independent human labels, statistical replication or model inference.", "",
             f"The separate denotation/aggregation code checked all {audit['v2']['records_checked']} v2 records and {audit['v3']['records_checked']:,} v3 records, with exact case/arm/budget completeness. Every saved v3 trace and answer sequence matches a separately implemented finite-set replay. Outcome flags and aggregate/stratified metrics agree. V2 paired descriptive family-bootstrap intervals were independently recomputed and match; their original weak inferential scope does not change.", "",
             "## Counterexample: pair separation is not one-question resolution", "",
             "Eight distinct, fully represented finite policies have four allowing and four denying consequences. Two legal binary questions share the same input and answer channel. `balanced` splits each decision class evenly: score 8, with both answer groups still mixed. `isolate` separates one denying policy from the other seven: score 4, with one pure denying branch. Both use a binary answer channel. The isolate question's singleton response identifies one of eight policies; binary channel size does not imply equal information in every response.", "",
             "A one-step resolution comparator counts public candidate IDs in answer groups whose finite decisions already agree. It assigns balanced 0/8 and isolate 1/8, selecting isolate without consulting the latent policy or gold label. It coincides with the real core's evaluated first-question comparator here. This equal candidate accounting is not a probability model of human intention, and the comparator is not claimed optimal beyond this one-step objective.", "",
             "The real EIV core strictly prefers score 8 over score 4. Its existing first-positive-score comparator chooses the declared isolate question first. All eight possible intended policies and every resulting truthful answer path are enumerated at budgets zero, one and two. This is a counterexample to budget-optimality, not a claim about the prevalence or human usability of these questions.", "",
             "| Budget | Targeted correct / 8 | First correct / 8 | Targeted abstain / 8 | First abstain / 8 | Targeted questions | First questions |", "|---|---:|---:|---:|---:|---:|---:|"]
    for budget, methods in counter["counts_by_budget"].items():
        target, first = methods["targeted"], methods["first"]
        lines.append(f"| {budget} | {target['correct_resolved_n']} | {first['correct_resolved_n']} | {target['abstention_n']} | {first['abstention_n']} | {target['questions_total']} | {first['questions_total']} |")
    lines += ["", "Neither method makes an incorrect resolved decision: coverage is complete and replies are truthful. At one question, first resolves 1/8 possibilities versus targeted 0/8. At two questions they tie on 1/8 resolution, with targeted using fewer questions. An explicit other or unsure answer abstains in all eight strategy/budget/reply checks. The equal candidate counts above are exhaustive finite accounting, not a calibrated or inferred probability distribution over people.", "",
              "## Consequence for the scientific claim", "", "V3 intentionally includes a question that perfectly separates all opposite-decision pairs, so the greedy score selects that question. Its positive result does not establish that the score generally optimizes resolution under a budget. This new example uses the unmodified core and retains the null/negative behavior. A future policy could optimize a declared expected-resolution or worst-case objective, but would need an explicit distribution or robustness criterion and a new prospective evaluation. No replacement policy is tuned into v3.", "",
              "## Reproduce", "", "`python3 -m eiv_experiment.selection_audit --output build/new-selection-audit`", "", "Use a fresh output directory. The manifest identifies audited evidence hashes, audit source and the unchanged core. Saved JSON contains the legal input, all 48 truthful candidate/strategy/budget records, eight nonselecting-reply checks and exact denominators. This check never calls a model, a network inference service or an actual file/message action."]
    return "\n".join(lines) + "\n"


def execute(output):
    output = Path(output)
    require(not output.exists(), "choose a new output directory; prior evidence is preserved")
    inputs = ["benchmark/v2/cases.jsonl", "results/engineering-v2/raw.jsonl", "results/engineering-v2/summary.json",
              "benchmark/v3/cases.jsonl", "results/dimensions-v3/raw.jsonl", "results/dimensions-v3/summary.json",
              "eiv/permissions.py", "eiv/logic.py", "eiv_experiment/dimensions.py", "research/protocol-v3.md"]
    hashes = {name: sha(ROOT / name) for name in inputs}
    audit = {"v2": audit_v2(read_jsonl(ROOT / inputs[0]), read_jsonl(ROOT / inputs[1]), json.loads((ROOT / inputs[2]).read_text())),
             "v3": audit_v3(read_jsonl(ROOT / inputs[3]), read_jsonl(ROOT / inputs[4]), json.loads((ROOT / inputs[5]).read_text()))}
    case, rows, counter = run_counterexample()
    require(all(sha(ROOT / name) == value for name, value in hashes.items()), "audited inputs changed during evaluation")
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    (output / "counterexample-case.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n")
    (output / "counterexample-raw.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    (output / "counterexample-summary.json").write_text(json.dumps(counter, indent=2, sort_keys=True) + "\n")
    (output / "analysis.md").write_text(markdown(audit, counter))
    (output / "audit-source.py").write_bytes(Path(__file__).read_bytes())
    manifest = {"kind": "post_exposure_independent_code_audit_and_constructive_counterexample", "created_unix": time.time(),
                "python": platform.python_version(), "human_review": False, "model_calls": 0,
                "audit_source_sha256": sha(Path(__file__)), "input_hashes": hashes,
                "output_hashes": {path.name: sha(path) for path in output.iterdir() if path.is_file()}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return audit, counter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit, counter = execute(args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"audited_v2_records": audit["v2"]["records_checked"], "audited_v3_records": audit["v3"]["records_checked"],
                      "counterexample_budget1": counter["counts_by_budget"]["1"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
