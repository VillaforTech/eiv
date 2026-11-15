"""Create review packet and one-time prospective freeze, never overwrite it."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def freeze():
    manifest = ROOT / "benchmark/manifest.json"
    if manifest.exists():
        raise SystemExit("Freeze already exists; refusing to overwrite")
    cases = [json.loads(line) for line in (ROOT / "benchmark/cases.jsonl").read_text().splitlines()]
    selected = [case for case in cases if case["case_id"].endswith("-01")]
    with (ROOT / "benchmark/human_review/review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case_id", "reviewer", "review_date", "instruction_plausible", "latent_intent_plausible", "reviewer_expected_decision", "agree_with_label", "disagreement_reason", "suggested_revision"])
        for case in selected:
            writer.writerow([case["case_id"]] + [""] * 8)
    packet = ["# Human review packet — 18 cases, all unreviewed\n",
              "Please first interpret each instruction yourself, then inspect the proposed latent policy and label. Record disagreement in review.csv; blank does not mean approval. This audit is not a personal reflection or an independent test certification.\n"]
    for case in selected:
        packet.extend([f"## {case['case_id']} ({case['split']})\n",
                       f"Instruction: {case['instruction']}\n",
                       f"Requested atom: `{json.dumps(case['request'], sort_keys=True)}`\n",
                       f"Visible facts: `{json.dumps(case['facts'], sort_keys=True)}`; latent facts: `{json.dumps(case['latent_facts'], sort_keys=True)}`\n",
                       f"Proposed latent policy: {case['latent_intent']['description']}\n",
                       f"Programmatic label: **{case['expected_decision']}**. Intervention: `{case['generator_perturbation']}`.\n",
                       "Review prompts: Is the latent policy plausible? Would a different intended reading be reasonable? Does the atom respect recipient, scope and conditions? Which answer would resolve the uncertainty?\n"])
    (ROOT / "benchmark/human_review/packet.md").write_text("\n".join(packet))
    files = ["benchmark/cases.jsonl", "benchmark/generate.py", "research/protocol.md", "eiv_experiment/replay.py"]
    data = {"version": "1", "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "user_local_date": "2026-10-12", "seed": 20261012,
            "status": "unreviewed synthetic engineering freeze; not a blinded holdout",
            "counts": dict(Counter(case["split"] for case in cases)),
            "family_counts": {split: len({c['family'] for c in cases if c['split'] == split}) for split in ('dev','validation','test')},
            "hashes": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
            "test_sha256": hashlib.sha256("\n".join(json.dumps(c, sort_keys=True) for c in cases if c["split"] == "test").encode()).hexdigest(),
            "human_review_status": "not performed"}
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__": freeze()
