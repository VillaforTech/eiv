"""Reproduce the frozen no-cost engineering comparison (not LLM efficacy)."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time

from eiv.permissions import analyze_request, evaluate_candidate, parse_instruction, validate_case
from .replay import export_requests, public_packet

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("direct", "conventional", "eiv", "eiv_no_exhaustive_verifier", "eiv_first_candidate", "eiv_first_question")
SEED = 20261012


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_cases(path=None):
    path = ROOT / "benchmark/v2/cases.jsonl" if path is None else Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_freeze(version="2"):
    directory = ROOT / ("benchmark" if version == "1" else "benchmark/v2")
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["hashes"].items():
        actual = sha(ROOT / name)
        if actual != expected:
            raise ValueError(f"frozen input changed: {name}; preserve v1 and document a new version")
    cases = load_cases(directory / "cases.jsonl")
    actual_test = hashlib.sha256("\n".join(json.dumps(c, sort_keys=True) for c in cases if c["split"] == "test").encode()).hexdigest()
    if actual_test != manifest["test_sha256"]:
        raise ValueError("canonical test hash changed")
    return manifest


def permission_key(candidate):
    normalized = []
    for item in candidate["permissions"]:
        entry = deepcopy(item)
        entry["resources"] = sorted(entry["resources"])
        entry["recipients"] = sorted(entry["recipients"], key=lambda x: "" if x is None else x)
        normalized.append(json.dumps(entry, sort_keys=True))
    return tuple(sorted(normalized))


def covers(candidates, latent):
    return any(permission_key(candidate) == permission_key(latent) for candidate in candidates)


def filter_candidates(packet, ids):
    packet = deepcopy(packet)
    packet["candidates"] = [c for c in packet["candidates"] if c["id"] in ids]
    for question in packet["questions"]:
        for answer in question["answers"]:
            answer["retain"] = [cid for cid in answer["retain"] if cid in ids]
        question["answers"] = [a for a in question["answers"] if a["retain"]]
    packet["questions"] = [q for q in packet["questions"] if len(q["answers"]) >= 2]
    if not packet["candidates"]: packet["semantic_status"] = "unknown"
    return validate_case(packet)


def generate_fixture(case):
    """Parse public text; explicit perturbations are test interventions only."""
    packet = parse_instruction(**public_packet(case))
    perturbation = case["generator_perturbation"]
    if perturbation == "none":
        return packet
    drop = "deny" if perturbation == "drop_deny_readings" else "allow"
    if perturbation not in {"drop_deny_readings", "drop_allow_readings"}:
        raise ValueError("unknown generator perturbation")
    ids = {c["id"] for c in packet["candidates"] if evaluate_candidate(packet["request"], packet["facts"], c)["decision"] != drop}
    return filter_candidates(packet, ids)


def answer_for(case, packet, question):
    if case["answer_behavior"] == "unsure": return "unsure"
    latent = case["latent_intent"]["candidate"]
    ids = {c["id"] for c in packet["candidates"] if permission_key(c) == permission_key(latent)}
    matches = [a["id"] for a in question["answers"] if ids.intersection(a["retain"])]
    return matches[0] if len(matches) == 1 else "other"


def run_one(case, arm):
    start = time.perf_counter()
    packet = generate_fixture(case)
    if arm == "eiv_first_candidate":
        packet = filter_candidates(packet, {packet["candidates"][0]["id"]} if packet["candidates"] else set())
    latent = case["latent_intent"]["candidate"]
    initial_coverage = covers(packet["candidates"], latent)
    answers, trace, questions = [], [], 0
    if arm == "direct":
        result = analyze_request(packet, max_questions=0)
    elif arm == "conventional" and " or " in case["instruction"]:
        # This conventional reference explicitly checks ambiguity even when a
        # generator omitted a reading and now reports unanimous candidate votes.
        # It asks the same available intent question and receives no extra facts.
        questions = 1
        matching = [c for c in packet["candidates"] if permission_key(c) == permission_key(latent)]
        answer = "unsure" if case["answer_behavior"] == "unsure" else matching[0]["id"] if matching else "other"
        trace.append({"event": "generic_clarification", "prompt": "Which interpretation is intended? Please specify the exact permission, or other/unsure.", "answer": answer})
        if answer in {"unsure", "other"}:
            result = {"decision": "abstain", "reason": "insufficient_answer" if answer == "unsure" else "intention_outside_candidates", "active_candidate_ids": [], "trace": trace[:]}
        else:
            narrowed = filter_candidates(packet, {answer})
            result = analyze_request(narrowed, max_questions=0)
    else:
        kwargs = {"max_questions": 2, "use_verifier": arm != "eiv_no_exhaustive_verifier",
                  "question_strategy": "first" if arm == "eiv_first_question" else "targeted"}
        result = analyze_request(packet, **kwargs)
        while result["decision"] == "ask" and questions < 2:
            question = result["suggested_question"]
            answer = answer_for(case, packet, question)
            answers.append({"question": question["id"], "answer": answer})
            questions += 1
            result = analyze_request(packet, answers=answers, **kwargs)
    decision = "abstain" if result["decision"] == "ask" else result["decision"]
    active = set(result.get("active_candidate_ids", []))
    after = [c for c in packet["candidates"] if c["id"] in active]
    return {"case_id": case["case_id"], "family": case["family"], "split": case["split"],
            "scenario_family": case.get("scenario_family", case["family"]),
            "arm": arm, "decision": decision, "expected_decision": case["expected_decision"],
            "correct_resolved": decision == case["expected_decision"],
            "false_authorization": decision == "allow" and case["expected_decision"] == "deny",
            "false_denial": decision == "deny" and case["expected_decision"] == "allow",
            "questions": questions, "initial_candidate_count": len(packet["candidates"]),
            "initial_candidate_coverage": initial_coverage, "final_candidate_coverage": covers(after, latent),
            "latency_seconds": time.perf_counter() - start,
            "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
            "monetary_cost_usd": 0.0, "cost_note": "no external inference; laptop energy/time not priced",
            "generator": "controlled_parser_with_declared_stress_intervention",
            "generator_perturbation": case["generator_perturbation"],
            "reason": result["reason"], "answers": answers, "generated_case": packet,
            "trace": trace + result.get("trace", []),
            "formal_outputs": result.get("candidates", [])}


def ratio(numerator, denominator):
    return None if denominator == 0 else numerator / denominator


def metrics(rows):
    n = len(rows)
    deny = sum(r["expected_decision"] == "deny" for r in rows)
    allow = n - deny
    fa = sum(r["false_authorization"] for r in rows)
    fd = sum(r["false_denial"] for r in rows)
    resolved = sum(r["decision"] in {"allow", "deny"} for r in rows)
    correct = sum(r["correct_resolved"] for r in rows)
    covered = sum(r.get("initial_candidate_coverage", False) for r in rows)
    generated = sum(r.get("initial_candidate_count", 0) > 0 for r in rows)
    latency = sorted(r["latency_seconds"] for r in rows)
    return {"n": n, "latent_deny_n": deny, "latent_allow_n": allow,
            "false_authorization_n": fa, "false_authorization_rate": ratio(fa, deny),
            "false_denial_n": fd, "false_denial_rate": ratio(fd, allow),
            "correct_resolved_n": correct, "correct_resolved_rate": ratio(correct, n),
            "resolved_n": resolved, "resolution_rate": ratio(resolved, n),
            "abstention_n": n - resolved, "abstention_rate": ratio(n-resolved, n),
            "selective_accuracy": ratio(correct, resolved),
            "initial_candidate_coverage_n": covered, "generated_candidate_cases_n": generated,
            "initial_candidate_coverage_rate_all": ratio(covered, n),
            "initial_candidate_coverage_rate_generated": ratio(covered, generated),
            "final_candidate_coverage_rate_all": ratio(sum(r.get("final_candidate_coverage", False) for r in rows), n),
            "questions_total": sum(r["questions"] for r in rows),
            "questions_mean": ratio(sum(r["questions"] for r in rows), n),
            "questions_distribution": dict(Counter(str(r["questions"]) for r in rows)),
            "latency_seconds_median": statistics.median(latency) if n else None,
            "latency_seconds_p90": latency[max(0, math.ceil(.9*n)-1)] if n else None,
            "model_calls": sum(r.get("usage", {}).get("calls", 0) for r in rows),
            "input_tokens": sum(r.get("usage", {}).get("input_tokens", 0) for r in rows),
            "output_tokens": sum(r.get("usage", {}).get("output_tokens", 0) for r in rows),
            "external_monetary_cost_usd": sum(r.get("monetary_cost_usd") or 0 for r in rows)}


def paired(rows, comparator, repetitions=2000):
    arms = {arm: {r["case_id"]: r for r in rows if r["arm"] == arm} for arm in ("eiv", comparator)}
    if set(arms["eiv"]) != set(arms[comparator]):
        raise ValueError("paired comparison requires same cases")
    families = sorted({r["family"] for r in arms["eiv"].values()})
    by_family = {family: [cid for cid, r in arms["eiv"].items() if r["family"] == family] for family in families}
    def differences(ids):
        left = metrics([arms["eiv"][cid] for cid in ids]); right = metrics([arms[comparator][cid] for cid in ids])
        return {key: None if left[key] is None or right[key] is None else left[key] - right[key]
                for key in ("false_authorization_rate", "correct_resolved_rate", "abstention_rate", "questions_mean")}
    point = differences(list(arms["eiv"]))
    samples = defaultdict(list)
    rng = random.Random(SEED)
    for _ in range(repetitions):
        ids = [cid for family in rng.choices(families, k=len(families)) for cid in by_family[family]]
        for key, value in differences(ids).items():
            if value is not None: samples[key].append(value)
    intervals = {}
    for key, values in samples.items():
        values.sort()
        intervals[key] = [values[int(.025*(len(values)-1))], values[int(.975*(len(values)-1))]]
    help_ids = [cid for cid in arms["eiv"] if arms["eiv"][cid]["correct_resolved"] and not arms[comparator][cid]["correct_resolved"]]
    harm_ids = [cid for cid in arms["eiv"] if not arms["eiv"][cid]["correct_resolved"] and arms[comparator][cid]["correct_resolved"]]
    tie_ids = [cid for cid in arms["eiv"] if arms["eiv"][cid]["correct_resolved"] == arms[comparator][cid]["correct_resolved"]]
    safety_harms = [cid for cid in arms["eiv"] if arms["eiv"][cid]["false_authorization"] and not arms[comparator][cid]["false_authorization"]]
    b, c = len(help_ids), len(harm_ids)
    discordance_p = min(1.0, 2 * sum(math.comb(b+c, k) for k in range(min(b,c)+1)) / 2**(b+c)) if b+c else 1.0
    return {"comparator": comparator, "difference_direction": "EIV minus comparator", "family_n": len(families),
            "point": point, "family_bootstrap_95_percentile": intervals, "resamples": repetitions,
            "seed": SEED, "warning": "descriptive only; few synthetic families, correlated variants, not independent evidence",
            "correctness_discordance": {"eiv_only_correct": b, "comparator_only_correct": c,
                                        "case_binomial_p_diagnostic_only": discordance_p,
                                        "not_valid_as_independent_sample_inference": True},
            "examples": {"helps": help_ids[:3], "no_change": tie_ids[:3], "harms": harm_ids[:3],
                         "false_authorization_harms": safety_harms[:3]}}


def summarize(rows):
    return {"kind": "controlled_engineering_not_llm_superiority", "human_labels_reviewed": False,
            "metrics": {arm: metrics([r for r in rows if r["arm"] == arm]) for arm in sorted({r['arm'] for r in rows})},
            "per_family": {family: {arm: metrics([r for r in rows if r["family"] == family and r["arm"] == arm])
                                     for arm in sorted({r['arm'] for r in rows})}
                           for family in sorted({r["family"] for r in rows})},
            "paired": [paired(rows, arm) for arm in sorted({r['arm'] for r in rows}) if arm != "eiv"]}


def markdown(summary):
    lines = ["# Controlled engineering results\n", "These are deterministic controlled-language policies, not an empirical LLM superiority result. Labels are synthetic and unreviewed; uncertainty is descriptive across template families.\n",
             "| Arm | False allow / latent deny | False deny / latent allow | Correct resolved / all | Abstain / all | Questions | Initial intent coverage / all |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for arm, m in summary["metrics"].items():
        lines.append(f"| {arm} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['correct_resolved_n']}/{m['n']} | {m['abstention_n']}/{m['n']} | {m['questions_total']} | {m['initial_candidate_coverage_n']}/{m['n']} |")
    lines += ["\nMissing-intent perturbations are deliberately induced stressors, not population prevalence. Candidate agreement still permits false authorization. Abstention is counted as unresolved, never as a correct answer.\n", "## Paired comparisons and examples\n"]
    for item in summary["paired"]:
        lines.append(f"### EIV versus {item['comparator']}\n")
        lines.append(f"Families: {item['family_n']}. Differences are EIV minus comparator. Correct-resolved difference {item['point']['correct_resolved_rate']:.3f}; descriptive family-bootstrap interval {item['family_bootstrap_95_percentile']['correct_resolved_rate']}.\n")
        for kind, ids in item["examples"].items(): lines.append(f"- {kind}: {', '.join(ids) if ids else 'none observed'}")
        lines.append("")
    lines += ["## Limits\n", "The first-question ablation may be identical because this grammar exposes only one full-interpretation question. The direct-Boolean ablation preserves permission semantics and is expected to match exhaustive checking. Neither null contrast establishes that verification or targeted question selection is useless in richer systems. Latency is local and machine-dependent; local energy/hardware costs are not priced. Raw JSONL preserves every generated case, decision and trace; summary.json contains denominators, cost, per-family results and descriptive uncertainty."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "validation", "test", "all"], default="test")
    parser.add_argument("--benchmark-version", choices=["1", "2"], default="2")
    parser.add_argument("--output", type=Path, default=ROOT / "results/engineering-v2")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--export-model-requests", type=Path)
    args = parser.parse_args()
    freeze = verify_freeze(args.benchmark_version)
    directory = ROOT / ("benchmark" if args.benchmark_version == "1" else "benchmark/v2")
    if args.verify_only:
        print("Frozen benchmark, generator, protocol and prompts verified.")
        return
    cases = [c for c in load_cases(directory / "cases.jsonl") if args.split == "all" or c["split"] == args.split]
    if args.export_model_requests:
        print(f"Exported {export_requests(cases, args.export_model_requests)} matched initial model requests.")
        return
    if args.output.exists():
        parser.error("output exists; choose a new path to preserve raw results")
    args.output.mkdir(parents=True)
    run_manifest = {"kind": "controlled_engineering_not_llm_superiority", "started_unix": time.time(),
                    "split": args.split, "seed": SEED, "python": platform.python_version(),
                    "benchmark_version": args.benchmark_version,
                    "benchmark_manifest_sha256": sha(directory / "manifest.json"),
                    "benchmark_sha256": sha(directory / "cases.jsonl"),
                    "test_sha256": freeze["test_sha256"], "cases": [c["case_id"] for c in cases],
                    "code_hashes": {p: sha(ROOT/p) for p in ["eiv_experiment/run.py", "eiv/permissions.py", "eiv/logic.py"]}}
    (args.output / "manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    rows = [run_one(case, arm) for case in cases for arm in ARMS]
    raw_path = args.output / "raw.jsonl"
    raw_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    summary = summarize(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (args.output / "analysis.md").write_text(markdown(summary))
    run_manifest.update({"finished_unix": time.time(), "raw_sha256": sha(raw_path)})
    (args.output / "manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    print(f"Reproduced {len(cases)} cases × {len(ARMS)} controlled policies; artifacts: {args.output}")


if __name__ == "__main__": main()
