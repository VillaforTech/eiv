"""Replay historical results with exact archived v0.3 sources, offline.

Current code can evolve without silently rewriting the original source freeze.
Hashes prove consistency with this checkout, not authenticity of its author.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path("evidence/frozen-v0.3")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def safe_relative(name):
    path = Path(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("unsafe archived path")
    return path


def verified_payloads(root=ROOT):
    """Validate the complete snapshot before creating an executable workspace."""
    root = Path(root)
    manifest = json.loads((root / ARCHIVE / "manifest.json").read_text())
    if manifest.get("schema") != "eiv-frozen-replay-1":
        raise ValueError("unsupported frozen replay manifest")
    payloads = {}
    for kind, base in (("source_hashes", root / ARCHIVE), ("evidence_hashes", root)):
        for name, expected in manifest[kind].items():
            path = safe_relative(name)
            if name in payloads:
                raise ValueError("source/evidence path collision: " + name)
            payload = (base / path).read_bytes()
            if digest(payload) != expected:
                raise ValueError("frozen " + kind + " mismatch: " + name)
            payloads[name] = payload
    present = {str(p.relative_to(root / ARCHIVE)) for p in (root / ARCHIVE).rglob("*.py")}
    listed = {name for name in manifest["source_hashes"] if name.endswith(".py")}
    if present != listed:
        raise ValueError("archived executable source differs from manifest")
    return manifest, payloads


def scrub_latency(value):
    if isinstance(value, dict):
        return {key: scrub_latency(item) for key, item in value.items()
                if "latency" not in key and key not in {"started_unix", "finished_unix"}}
    if isinstance(value, list):
        return [scrub_latency(item) for item in value]
    return value


def json_content(path):
    text = path.read_text()
    return [json.loads(line) for line in text.splitlines() if line.strip()] if path.suffix == ".jsonl" else json.loads(text)


def run_replay(output, root=ROOT):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("output exists; choose a new path to preserve evidence")
    manifest, payloads = verified_payloads(root)
    output.mkdir(parents=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix="eiv-frozen-replay-") as temporary:
        stage = Path(temporary)
        for name, payload in payloads.items():
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        environment = dict(os.environ, PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
        for key in ("PYTHONPATH", "PYTHONHOME"):
            environment.pop(key, None)

        def run(name, command):
            result = subprocess.run([sys.executable, *command], cwd=stage, env=environment,
                                    capture_output=True, text=True)
            (output / (name + ".txt")).write_text(result.stdout + result.stderr)
            checks.append({"check": name, "exit_code": result.returncode})
            if result.returncode:
                raise RuntimeError(name + " failed; inspect its log in " + str(output))

        def compare(actual, reference, exact=True):
            first, second = output / actual, stage / reference
            same = first.read_bytes() == second.read_bytes() if exact else (
                scrub_latency(json_content(first)) == scrub_latency(json_content(second)))
            if not same:
                raise ValueError("historical replay differs: " + reference)

        run("v1_freeze", ["-c", "from eiv_experiment.run import verify_freeze; verify_freeze('1')"])
        run("v2_freeze", ["-m", "eiv_experiment.run", "--verify-only"])
        run("v3_freeze", ["-m", "eiv_experiment.dimensions", "--verify-only"])
        run("legacy", ["-m", "eiv", "benchmark", "--output", str(output / "legacy.json")])
        compare("legacy.json", "results/audit-legacy.json", exact=False)
        run("engineering", ["-m", "eiv_experiment.run", "--split", "test", "--output", str(output / "engineering")])
        for name in ("raw.jsonl", "summary.json"):
            compare("engineering/" + name, "results/engineering-v2/" + name, exact=False)
        run("llm_replay", ["-m", "eiv_llm.analyze", "results/llm-pilot-v2.jsonl", "--output", str(output / "llm-replay")])
        compare("llm-replay/summary.json", "results/llm-pilot-v2-analysis/summary.json")
        pilot = json.loads((stage / "results/llm-pilot-v2.manifest.json").read_text())
        for key, name in (("driver_sha256", "driver.py"), ("prompts_sha256", "prompts.py"), ("schema_sha256", "schema.json")):
            if digest((stage / "results/llm-pilot-v2-source" / name).read_bytes()) != pilot[key]:
                raise ValueError("original pilot source hash mismatch: " + name)
        run("dimensions", ["-m", "eiv_experiment.dimensions", "--output", str(output / "dimensions")])
        for name in ("raw.jsonl", "summary.json", "analysis.md"):
            compare("dimensions/" + name, "results/dimensions-v3/" + name)
        recorded = json.loads((stage / "results/dimensions-v3/manifest.json").read_text())
        for name, key in (("raw.jsonl", "raw_sha256"), ("summary.json", "summary_sha256")):
            if digest((stage / "results/dimensions-v3" / name).read_bytes()) != recorded[key]:
                raise ValueError("original v3 output hash mismatch: " + name)
        run("selection_audit", ["-m", "eiv_experiment.selection_audit", "--output", str(output / "selection-audit")])
        for name in ("audit.json", "counterexample-case.json", "counterexample-raw.jsonl",
                     "counterexample-summary.json", "analysis.md", "audit-source.py"):
            compare("selection-audit/" + name, "results/selection-audit-final-20261023/" + name)
    report = {
        "python": platform.python_version(),
        "source_version": manifest["source_version"],
        "source_commit": manifest["source_commit"],
        "archived_sources_verified": len(manifest["source_hashes"]),
        "evidence_files_verified": len(manifest["evidence_hashes"]),
        "checks": checks,
        "historical_v2_rows": 240,
        "historical_v3_rows": 28800,
        "v3_exact_replay": True,
        "selection_audit_exact_replay": True,
        "saved_model_analysis_replayed_without_inference": True,
        "scope": "Historical software reproducibility; no new empirical or human validation.",
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run_replay(args.output), indent=2))


if __name__ == "__main__":
    main()
