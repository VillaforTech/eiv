"""Amend v1 by grouping observable instruction templates, not scenario labels.

Preserves all v1 cases and latent labels. Never overwrites the v2 freeze.
"""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent


def canonical_template(case):
    clauses = case["instruction"].rstrip(".").split(";")
    relevant = [clause for clause in clauses if case["request"]["resource"] in clause]
    # Preserve one template for instructions without a requested-resource grant;
    # dropping unrelated conjuncts catches scope-choice plus irrelevant exception.
    selected = relevant or clauses
    text = ";".join(clause.strip() for clause in selected)
    text = re.sub(r"\b(read|write|delete|send)\b", "ACTION", text)
    text = re.sub(r"\b(report\d+_\d+|summary\d+_\d+|archive\d+)\b", "RESOURCE", text)
    text = re.sub(r"\b(alex\d+|bea\d+)\b", "RECIPIENT", text)
    text = text.replace(" to RECIPIENT or RECIPIENT", " TO_RECIPIENT_CHOICE")
    text = text.replace(" to RECIPIENT", "")
    text = re.sub(r"\bapproved\b", "CONDITION", text)
    return text


def build_cases():
    original = [json.loads(line) for line in (ROOT/"benchmark/cases.jsonl").read_text().splitlines()]
    groups = defaultdict(list)
    for case in original: groups[canonical_template(case)].append(case)
    priority = {"dev": 0, "validation": 1, "test": 2}
    output = []
    for template, cases in groups.items():
        split = max((case["split"] for case in cases), key=priority.__getitem__)
        group_id = "template_" + hashlib.sha256(template.encode()).hexdigest()[:12]
        for case in cases:
            case["scenario_family"] = case["family"]
            case["original_v1_split"] = case["split"]
            case["family"] = group_id
            case["template_id"] = group_id
            case["normalized_template"] = template
            case["split"] = split
            case["provenance"]["version"] = "2"
            case["provenance"]["amendment"] = "structural template split correction after v1 engineering exposure; before test LLM exposure"
            output.append(case)
    return sorted(output, key=lambda case: case["case_id"])


def freeze():
    if (DIRECTORY/"manifest.json").exists(): raise SystemExit("v2 freeze exists; refusing overwrite")
    cases = build_cases()
    (DIRECTORY/"cases.jsonl").write_text("".join(json.dumps(c, sort_keys=True)+"\n" for c in cases))
    selected = [c for c in cases if c["case_id"].endswith("-01")]
    with (DIRECTORY/"human_review/review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case_id", "reviewer", "review_date", "instruction_plausible", "latent_intent_plausible", "reviewer_expected_decision", "agree_with_label", "disagreement_reason", "suggested_revision"])
        for case in selected: writer.writerow([case["case_id"]]+[""]*8)
    packet = ["# V2 human review: 18 scenario cases, all unreviewed\n", "Fill review.csv independently. All latent policies and labels are programmatic proposals, not approved human judgments. Record disagreement and proposed changes without silently replacing frozen labels.\n"]
    for c in selected:
        packet.extend([f"## {c['case_id']} ({c['split']}; {c['family']})\n",
                       f"Instruction: {c['instruction']}\n",
                       f"Request: `{json.dumps(c['request'], sort_keys=True)}`\n",
                       f"Visible facts: `{json.dumps(c['facts'])}`; latent facts: `{json.dumps(c['latent_facts'])}`\n",
                       f"Proposed intended policy: {c['latent_intent']['description']}\n",
                       f"Proposed classification: **{c['expected_decision']}**; engineering stressor: {c['generator_perturbation']}.\n",
                       "Is this intent plausible from the instruction? What alternatives are missing? Is the requested scope authorized? What would you answer to a clarification?\n"])
    (DIRECTORY/"human_review/packet.md").write_text("\n".join(packet))
    files = ["benchmark/v2/cases.jsonl", "benchmark/v2/build.py", "research/protocol.md", "research/protocol-v2-amendment.md", "eiv_experiment/replay.py"]
    manifest = {"version": "2", "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "user_local_date": "2026-10-12",
                "seed": 20261012, "status": "unreviewed engineering split correction; v1 engineering exposed; no test LLM exposure before this freeze",
                "counts": dict(Counter(c["split"] for c in cases)),
                "family_counts": {s: len({c['family'] for c in cases if c['split'] == s}) for s in ('dev','validation','test')},
                "hashes": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
                "test_sha256": hashlib.sha256("\n".join(json.dumps(c, sort_keys=True) for c in cases if c["split"] == "test").encode()).hexdigest(),
                "human_review_status": "not performed", "supersedes": "benchmark/manifest.json for active split only; preserves v1"}
    (DIRECTORY/"manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__": freeze()
