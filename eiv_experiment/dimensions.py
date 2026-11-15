"""Exposed controlled study of bounded, dimension-specific clarification.

This module never calls a model or executes a requested operation. The policy
receives only public candidates, finite checks and answer IDs. The separate
oracle can inspect latent dimensions, and reveals only the dimension asked.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time

from eiv.logic import ValidationError
from eiv.permissions import evaluate_candidate, validate_case

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmark/v3"
PROTOCOL = ROOT / "research/protocol-v3.md"
SCHEMA = "eiv-dimensions-3.0"
ARMS = ("direct", "ordinary_first", "fixed_order", "eiv_targeted", "abstain_all")
BUDGETS = (0, 1, 2, 3)
FAMILIES = ("resource", "action", "recipient", "duration", "condition", "prohibition")
CONDITIONS = ("complete", "omit_restrictive", "omit_permissive", "unsure", "missing_latent_other")
SOURCE_PATHS = ("eiv_experiment/dimensions.py", "eiv/permissions.py", "eiv/logic.py", "research/protocol-v3.md")


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def permission(action, resource, recipient=None, scope="once", effect="allow", conditions=None):
    return {"effect": effect, "action": action, "resources": [resource],
            "recipients": [recipient], "scope": scope, "conditions": conditions or {}}


def _policy(family, bits):
    """Author a finite policy; the first dimension determines the operation."""
    p, n1, n2 = bits
    if family == "recipient":
        request = {"domain": "messages", "action": "send", "resource": "report", "recipient": "alex", "scope": "once"}
        main = permission("send", "report", "alex" if p else "bea")
        extras = [permission("send", "archive", "chen" if n1 else "dana"),
                  permission("send", "memo", "eli", "session" if n2 else "once")]
        facts = {}
    else:
        request = {"domain": "files", "action": "read", "resource": "report", "recipient": None, "scope": "once"}
        facts = {}
        if family == "resource":
            main = permission("read", "report" if p else "payroll")
        elif family == "action":
            main = permission("read" if p else "write", "report")
        elif family == "duration":
            request["scope"] = "session"
            main = permission("read", "report", scope="session" if p else "once")
        elif family == "condition":
            facts = {"approved": True}
            main = permission("read", "report", conditions={"approved": bool(p)})
        elif family == "prohibition":
            main = permission("read", "report", effect="allow" if p else "deny")
        else:
            raise ValueError("unknown family")
        extras = [permission("write", "archive" if n1 else "backup"),
                  permission("read", "memo", scope="session" if n2 else "once")]
    return request, facts, [main] + extras


def _dimension_labels(family):
    primary = {
        "resource": ("Which resource may be read?", ["payroll", "report"]),
        "action": ("Which action on report is permitted?", ["write", "read"]),
        "recipient": ("Who may receive report?", ["bea", "alex"]),
        "duration": ("How long does the report permission extend?", ["once", "session"]),
        "condition": ("Which approved value is required to read report?", ["false", "true"]),
        "prohibition": ("What is the rule for reading report?", ["explicit deny", "explicit allow"]),
    }
    return [primary[family],
            ("Who may receive archive?", ["dana", "chen"]) if family == "recipient" else
            ("Which unrelated resource may be written?", ["backup", "archive"]),
            ("How long does the unrelated memo permission extend?", ["once", "session"])]


def generate_cases():
    """Return deterministic, counterbalanced, explicitly exposed stress inputs."""
    rows = []
    all_bits = list(itertools.product((0, 1), repeat=3))
    for family in FAMILIES:
        request, facts, _ = _policy(family, (0, 0, 0))
        labels = _dimension_labels(family)
        candidates = []
        dimensions = {}
        for bits in all_bits:
            cid = "c" + "".join(str(bit) for bit in bits)
            dimensions[cid] = list(bits)
            description = "; ".join(f"{labels[i][0]} {labels[i][1][bit]}" for i, bit in enumerate(bits))
            candidates.append({"id": cid, "interpretation": description,
                               "permissions": _policy(family, bits)[2]})
        for latent_bits in all_bits:
            latent_id = "c" + "".join(str(bit) for bit in latent_bits)
            for condition in CONDITIONS:
                present = [c for c in candidates if
                           not (condition == "omit_restrictive" and dimensions[c["id"]][0] == 0) and
                           not (condition == "omit_permissive" and dimensions[c["id"]][0] == 1) and
                           not (condition == "missing_latent_other" and c["id"] == latent_id)]
                for order in itertools.permutations(range(3)):
                    questions = []
                    for dim in order:
                        answers = [{"id": f"v{bit}", "label": labels[dim][1][bit],
                                    "retain": [c["id"] for c in present if dimensions[c["id"]][dim] == bit]}
                                   for bit in (0, 1)]
                        # Dropping a whole polarity removes its now-nonquestion.
                        if all(answer["retain"] for answer in answers):
                            questions.append({"id": f"d{dim}", "prompt": labels[dim][0], "answers": answers})
                    public = {"schema_version": "1.0", "semantic_status": "structured",
                              "instruction": "Controlled policy alternatives: select the intended value for each explicitly listed dimension. Each candidate is one entire possible policy.",
                              "request": request, "facts": facts,
                              "candidates": present, "questions": questions}
                    validate_case(public)
                    cid = f"{family}-{''.join(map(str, latent_bits))}-{condition}-o{''.join(map(str, order))}"
                    rows.append({"case_id": cid, "family": family, "condition": condition,
                                 "question_order": list(order), "public": deepcopy(public),
                                 "oracle": {"dimensions": list(latent_bits), "latent_candidate_id": latent_id,
                                            "behavior": "unsure" if condition == "unsure" else "other" if condition == "missing_latent_other" else "truthful"},
                                 "gold_decision": "allow" if latent_bits[0] else "deny",
                                 "initial_candidate_coverage": latent_id in {c["id"] for c in present}})
    return rows


def dimension_answer(question, oracle):
    """Only a selected dimension ID crosses the oracle/policy boundary."""
    behavior = oracle["behavior"]
    if behavior in {"other", "unsure"}:
        return behavior
    if behavior != "truthful":
        raise ValueError("unsupported oracle behavior")
    qid = question.get("id")
    if qid not in {"d0", "d1", "d2"}:
        raise ValueError("oracle answers only declared dimension questions")
    return "v" + str(oracle["dimensions"][int(qid[1])])


def select_question(questions, checks, active_ids, strategy):
    """Choose using public partitions and verifier outcomes, never oracle data.

    EIV and ordinary_first match the original core selector. fixed_order also
    asks about a partition with zero separated unlike-decision pairs.
    """
    if strategy not in {"targeted", "first", "fixed"}:
        raise ValueError("unknown question strategy")
    active = set(active_ids)
    decisions = {check["id"]: check["decision"] for check in checks}
    ranked = []
    for order, question in enumerate(questions):
        groups = [set(answer["retain"]) & active for answer in question["answers"]]
        groups = [group for group in groups if group]
        if len(groups) < 2:
            continue
        score = sum(decisions[a] != decisions[b]
                    for i, group in enumerate(groups) for other in groups[i + 1:]
                    for a in group for b in other)
        if score or strategy == "fixed":
            ranked.append((score if strategy == "targeted" else 0, -order, question, score))
    if not ranked:
        return None
    chosen = max(ranked, key=lambda item: item[:2])
    return {"question": deepcopy(chosen[2]), "separated_decision_pairs": chosen[3]}


def policy_step(public, checks, answers, budget, arm):
    """Pure replay, separated from answer production and evaluation labels."""
    validate_case(public)
    if arm not in ARMS:
        raise ValueError("unknown arm")
    if not isinstance(answers, list) or type(budget) is not int or not 0 <= budget <= 3 or len(answers) > budget:
        raise ValueError("invalid question budget/history")
    ids = [candidate["id"] for candidate in public["candidates"]]
    if (not isinstance(checks, list) or len(checks) != len(ids) or
            any(not isinstance(check, dict) or check.get("decision") not in {"allow", "deny", "abstain"} for check in checks) or
            {check.get("id") for check in checks} != set(ids)):
        raise ValidationError("one finite decision per public candidate is required")
    if arm in {"direct", "abstain_all"} and answers:
        raise ValueError("noninteractive arm cannot receive oracle answers")
    active = [candidate["id"] for candidate in public["candidates"]]
    trace = []
    strategy = {"ordinary_first": "first", "fixed_order": "fixed"}.get(arm, "targeted")
    for index in range(len(answers) + 1):
        statuses = [row["decision"] for row in checks if row["id"] in active]
        selected = None
        if arm == "abstain_all":
            decision, reason = "abstain", "abstain_all_control"
        elif public["semantic_status"] == "unknown" or not active:
            decision, reason = "abstain", "semantic_generation_unavailable"
        elif all(status == "allow" for status in statuses):
            decision, reason = "allow", "candidate_consensus_conditional_on_coverage"
        elif all(status == "deny" for status in statuses):
            decision, reason = "deny", "candidate_consensus_conditional_on_coverage"
        elif arm == "direct":
            decision, reason = "abstain", "no_clarification_control"
        else:
            selected = select_question(public["questions"], checks, active, strategy)
            if selected and index < budget:
                decision, reason = "ask", "candidate_decisions_disagree"
            else:
                decision, reason = "abstain", "question_budget_exhausted" if selected else "unresolved_interpretation"
                selected = None
        if index == len(answers):
            return {"decision": decision, "reason": reason, "active_candidate_ids": active,
                    "questions_used": index, "suggested_question": selected, "trace": trace}
        reply = answers[index]
        if decision != "ask" or set(reply) != {"question", "answer"} or reply["question"] != selected["question"]["id"]:
            raise ValidationError("answer must match the currently selected question")
        before = active[:]
        answer_id = reply["answer"]
        if answer_id in {"other", "unsure"}:
            if index + 1 != len(answers):
                raise ValidationError("nonselecting answer terminates the interaction")
            trace.append({"question": reply["question"], "answer": answer_id, "before": before, "after": active[:],
                          "separated_decision_pairs": selected["separated_decision_pairs"]})
            return {"decision": "abstain", "reason": "intention_outside_candidates" if answer_id == "other" else "insufficient_answer",
                    "active_candidate_ids": active, "questions_used": index + 1, "suggested_question": None, "trace": trace}
        answer = next((row for row in selected["question"]["answers"] if row["id"] == answer_id), None)
        if answer is None:
            raise ValidationError("unknown answer ID")
        active = [cid for cid in active if cid in answer["retain"]]
        trace.append({"question": reply["question"], "answer": answer_id, "before": before, "after": active[:],
                      "separated_decision_pairs": selected["separated_decision_pairs"]})
        if not active:
            if index + 1 != len(answers):
                raise ValidationError("incompatible answer terminates the interaction")
            return {"decision": "abstain", "reason": "incompatible_answer", "active_candidate_ids": [],
                    "questions_used": index + 1, "suggested_question": None, "trace": trace}
    raise AssertionError("unreachable")


def run_one(case, arm, budget, checks=None):
    public = deepcopy(case["public"])
    validate_case(public)
    if checks is None:
        checks = [evaluate_candidate(public["request"], public["facts"], candidate) for candidate in public["candidates"]]
    answers = []
    result = policy_step(public, checks, answers, budget, arm)
    while result["decision"] == "ask":
        question = result["suggested_question"]["question"]
        answers.append({"question": question["id"], "answer": dimension_answer(question, case["oracle"])})
        result = policy_step(public, checks, answers, budget, arm)
    decision = result["decision"]
    return {"case_id": case["case_id"], "family": case["family"], "condition": case["condition"],
            "question_order": case["question_order"], "primary_question_position": case["question_order"].index(0) + 1,
            "arm": arm, "budget": budget, "gold_decision": case["gold_decision"],
            "decision": decision, "reason": result["reason"], "questions": len(answers),
            "dimension_answer_disclosures": sum(answer["answer"] not in {"other", "unsure"} for answer in answers),
            "nonselecting_replies": sum(answer["answer"] in {"other", "unsure"} for answer in answers),
            "false_authorization": decision == "allow" and case["gold_decision"] == "deny",
            "false_denial": decision == "deny" and case["gold_decision"] == "allow",
            "correct_resolved": decision == case["gold_decision"],
            "initial_candidate_coverage": case["initial_candidate_coverage"],
            "retained_candidate_coverage": case["oracle"]["latent_candidate_id"] in result["active_candidate_ids"],
            "candidate_count": len(public["candidates"]), "active_candidate_ids": result["active_candidate_ids"],
            "formal_statuses": {row["id"]: row["formal_result"]["status"] for row in checks},
            "oracle_access": answers, "trace": result["trace"], "simulated": True}


def metrics(rows):
    n = len(rows)
    deny = sum(row["gold_decision"] == "deny" for row in rows)
    allow = n - deny
    false_allow = sum(row["false_authorization"] for row in rows)
    false_deny = sum(row["false_denial"] for row in rows)
    correct = sum(row["correct_resolved"] for row in rows)
    abstain = sum(row["decision"] == "abstain" for row in rows)
    questions = sum(row["questions"] for row in rows)
    return {"n": n, "latent_deny_n": deny, "latent_allow_n": allow,
            "false_authorization_n": false_allow, "false_authorization_rate": false_allow / deny if deny else None,
            "false_denial_n": false_deny, "false_denial_rate": false_deny / allow if allow else None,
            "correct_resolved_n": correct, "correct_resolved_rate": correct / n if n else None,
            "abstention_n": abstain, "abstention_rate": abstain / n if n else None,
            "resolved_n": n - abstain, "selective_accuracy": correct / (n - abstain) if n != abstain else None,
            "questions_total": questions, "questions_mean": questions / n if n else None,
            "dimension_answer_disclosures": sum(row["dimension_answer_disclosures"] for row in rows),
            "nonselecting_replies": sum(row["nonselecting_replies"] for row in rows),
            "questions_distribution": {str(k): sum(row["questions"] == k for row in rows) for k in BUDGETS},
            "initial_candidate_coverage_n": sum(row["initial_candidate_coverage"] for row in rows),
            "retained_candidate_coverage_n": sum(row["retained_candidate_coverage"] for row in rows)}


def _by_budget(rows):
    return {str(budget): {arm: metrics([r for r in rows if r["budget"] == budget and r["arm"] == arm])
                         for arm in ARMS} for budget in BUDGETS}


def summarize(rows):
    return {"schema": SCHEMA, "kind": "exposed_controlled_dimension_oracle_engineering",
            "human_labels_reviewed": False, "model_calls": 0, "external_monetary_cost_usd": 0,
            "uncertainty": "Exact finite constructed-space counts; no population or independent-family confidence claim.",
            "records": len(rows), "case_count": len({r["case_id"] for r in rows}), "arms": list(ARMS),
            "budgets": list(BUDGETS), "metrics_by_budget": _by_budget(rows),
            "by_condition": {condition: _by_budget([r for r in rows if r["condition"] == condition]) for condition in CONDITIONS},
            "by_family": {family: _by_budget([r for r in rows if r["family"] == family]) for family in FAMILIES},
            "by_primary_question_position": {str(position): _by_budget([r for r in rows if r["primary_question_position"] == position]) for position in (1, 2, 3)}}


def markdown(summary):
    lines = ["# v3 dimension-only clarification: exposed engineering result", "",
             "AI-authored and inspected finite scenarios; labels are programmatic and unreviewed. No LLM, human participant, real permission enforcement or blind confirmatory evaluation was run.", "",
             f"{summary['case_count']:,} constructed cases, {summary['records']:,} outcome records, six question orders and question budgets 0/1/2/3. An oracle returns only the chosen dimension answer ID. Repeated orders and budgets are correlated, not extra independent evidence.", "",
             "## Complete coverage, one-question budget", "",
             "| Arm | Correct resolved / all | False allow / latent deny | False deny / latent allow | Abstain / all | Questions |", "|---|---:|---:|---:|---:|---:|"]
    for arm, m in summary["by_condition"]["complete"]["1"].items():
        lines.append(f"| {arm} | {m['correct_resolved_n']}/{m['n']} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['abstention_n']}/{m['n']} | {m['questions_total']} |")
    lines += ["", "The targeted policy selects the authorization dimension. Fixed-order policies reach that dimension first in one third of the counterbalanced orders; this is constructed structure, not measured natural-language behavior. With three questions, both first policies resolve every complete-coverage case. There is no measured difference between ordinary_first and fixed_order here: each nuisance partition still separates some unlike-decision pairs.", "", "## Coverage and answer failures, one-question budget", "", "| Condition | Arm | False allow / latent deny | False deny / latent allow | Correct resolved / all | Abstain / all | Questions |", "|---|---|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS[1:]:
        for arm in ("ordinary_first", "eiv_targeted"):
            m = summary["by_condition"][condition]["1"][arm]
            lines.append(f"| {condition} | {arm} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['correct_resolved_n']}/{m['n']} | {m['abstention_n']}/{m['n']} | {m['questions_total']} |")
    lines += ["", "Omitting every restrictive reading leaves an unsafe permissive consensus; omitting every permissive reading yields false denial. The oracle is never called after consensus. An explicit other/unsure answer terminates with abstention when a question is actually asked. Therefore targeted selection does not solve interpretation coverage.", "", "## Reproduction and interpretation", "", "The manifest freezes dataset bytes, this module, the protocol and the finite core before execution. Raw rows retain candidate IDs, formal statuses, selected-question scores, oracle answer IDs, restriction traces and outcome flags. Summary denominators are exact and stratified by budget, condition, family and question position. There are no bootstrap confidence bands: this exhausts a tiny author-constructed space and is not a random sample. Local electricity, hardware and development time are unpriced.", "", "Run `python3 -m eiv_experiment.dimensions --verify-only` to verify the freeze; use a fresh `--output` directory to reproduce all 28,800 outcomes without inference or external services."]
    return "\n".join(lines) + "\n"


def prepare(directory=DATA):
    """Freeze once before outcomes; never replace an existing data version."""
    directory = Path(directory)
    if directory.exists():
        raise ValueError("freeze directory exists; preserve it and choose a new directory")
    directory.mkdir(parents=True)
    rows = generate_cases()
    path = directory / "cases.jsonl"
    path.write_text("".join(_canonical(row) + "\n" for row in rows))
    manifest = {"schema": SCHEMA, "kind": "prospective_local_engineering_freeze_after_design_exposure",
                "prepared_unix": time.time(), "human_labels_reviewed": False,
                "case_count": len(rows), "families": list(FAMILIES), "conditions": list(CONDITIONS),
                "question_order_count": 6, "latent_policies_per_family": 8,
                "cases_sha256": _hash(path), "source_hashes": {name: _hash(ROOT / name) for name in SOURCE_PATHS}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def verify_freeze(directory=DATA):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("schema") != SCHEMA or manifest.get("cases_sha256") != _hash(directory / "cases.jsonl"):
        raise ValueError("dataset version or checksum differs from v3 freeze")
    if set(manifest["source_hashes"]) != set(SOURCE_PATHS):
        raise ValueError("freeze must identify every required source")
    for name, expected in manifest["source_hashes"].items():
        if _hash(ROOT / name) != expected:
            raise ValueError("source differs from frozen v3 study: " + name)
    rows = [json.loads(line) for line in (directory / "cases.jsonl").read_text().splitlines()]
    if len(rows) != manifest["case_count"] or rows != generate_cases():
        raise ValueError("frozen cases do not match deterministic generation")
    return manifest, rows


def execute(output, directory=DATA):
    manifest, cases = verify_freeze(directory)
    output = Path(output)
    if output.exists():
        raise ValueError("output exists; preserve previous outcomes and choose a new path")
    output.mkdir(parents=True)
    started = time.time()
    run_manifest = {"schema": SCHEMA, "started_unix": started, "python": platform.python_version(),
                    "freeze_manifest_sha256": _hash(Path(directory) / "manifest.json"),
                    "cases_sha256": manifest["cases_sha256"], "source_hashes": manifest["source_hashes"],
                    "arms": list(ARMS), "budgets": list(BUDGETS), "case_count": len(cases)}
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    rows = []
    for case in cases:
        public = case["public"]
        checks = [evaluate_candidate(public["request"], public["facts"], candidate) for candidate in public["candidates"]]
        for budget in BUDGETS:
            for arm in ARMS:
                rows.append(run_one(case, arm, budget, checks))
    raw = output / "raw.jsonl"
    raw.write_text("".join(_canonical(row) + "\n" for row in rows))
    summary = summarize(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (output / "analysis.md").write_text(markdown(summary))
    run_manifest.update(finished_unix=time.time(), raw_sha256=_hash(raw),
                        summary_sha256=_hash(output / "summary.json"), records=len(rows))
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="freeze new inputs before evaluating outcomes")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=ROOT / "results/dimensions-v3")
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.verify_only:
                parser.error("prepare and verify-only are mutually exclusive")
            manifest = prepare(args.data)
            print(f"Froze {manifest['case_count']} exposed v3 engineering inputs; no outcomes evaluated.")
        elif args.verify_only:
            manifest, _ = verify_freeze(args.data)
            print(f"Verified {manifest['case_count']} frozen v3 inputs, protocol, study source and finite core.")
        else:
            summary = execute(args.output, args.data)
            print(f"Reproduced {summary['case_count']} exposed cases and {summary['records']} controlled outcomes: {args.output}")
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
