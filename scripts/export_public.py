"""Export an allowlisted public source tree without repository history.

Existing outputs are never replaced. All selected bytes are inspected before
writing; disallowed material fails the export rather than being silently edited.
The generated ignore file is the only canonicalized source artifact.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE_PATHS = (
    "eiv", "eiv_experiment", "eiv_llm", "tests", "fixtures", "examples", "schemas",
    "benchmark", ".github", "portfolio", "evidence",
    "results/engineering-v2", "results/dimensions-v3",
    "results/llm-pilot-v2-analysis", "results/llm-pilot-v2-source",
    "results/selection-audit-final-20261023", "results/planner-v4",
)
FILE_PATHS = (
    "README.md", "LICENSE", "CITATION.cff", "CONTRIBUTING.md", "SECURITY.md",
    "CHANGELOG.md", "GOVERNANCE.md", "CODE_OF_CONDUCT.md", "pyproject.toml", "requirements.lock", ".gitattributes",
    "docs/architecture.md", "docs/usage.md", "docs/reproducibility.md",
    "docs/research-report.md", "docs/project-status.md", "docs/formal-action-model.md", "docs/open-source.md",
    "research/protocol.md", "research/protocol-v2-amendment.md", "research/protocol-v3.md",
    "research/local-pilot-addendum.md", "research/post-pilot-corrections.md",
    "research/related-work.md", "research/references.bib",
    "results/audit-legacy.json", "results/llm-pilot-v2.jsonl", "results/llm-pilot-v2.manifest.json",
    "scripts/package_release.py", "scripts/reproduce.py", "scripts/replay_frozen.py",
    "scripts/export_public.py", "scripts/publish_github.py", "scripts/release_github.py", "scripts/restore_evidence.py",
    "docs/release-v0.4.0.md",
)
REQUIRED_PATHS = (
    "README.md", "LICENSE", "CITATION.cff", "CONTRIBUTING.md", "SECURITY.md",
    "CHANGELOG.md", "pyproject.toml", "requirements.lock", "eiv/__init__.py",
    "eiv/assets/workbench.html", "portfolio/index.html", "research/references.bib",
    "docs/architecture.md", "docs/usage.md", "docs/reproducibility.md",
    "docs/research-report.md", "docs/project-status.md", "docs/formal-action-model.md", "docs/open-source.md", "evidence/frozen-v0.3/manifest.json",
    "scripts/package_release.py", "scripts/reproduce.py", "scripts/replay_frozen.py",
    "scripts/export_public.py", ".github/workflows/ci.yml",
)
EXCLUDED_PARTS = {"__pycache__", "node_modules", ".git", ".venv", ".DS_Store", "source-snapshots"}
IGNORE_CONTENT = """__pycache__/
*.py[cod]
.venv*/
.DS_Store
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.env
.env.*
!.env.example
# Materialized frozen evidence; restore explicitly before tests or source export.
/results/dimensions-v3/raw.jsonl
/benchmark/v3/cases.jsonl
/results/engineering-v2/raw.jsonl
"""
# Split tokens keep the prohibited names out of the public source text itself.
PROHIBITED_CONTEXT = ("blue" + "dot", "shami" + "so", "chiton" + "go", "co" + "hort", "facil" + "itator")
SECRET_PATTERNS = (
    re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{15,}"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    re.compile(r"(?:codex|file)://[^\s]+"),
    re.compile(r"https://docs\.google\.com/document/d/[A-Za-z0-9_-]+"),
)


def approved_file(path, root):
    relative = path.relative_to(root)
    if any(part in EXCLUDED_PARTS or part.startswith(".venv") for part in relative.parts):
        return False
    if path.suffix in {".pyc", ".pyo"} or not path.is_file():
        return False
    # Never traverse links, including a symlinked parent directory.
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root and root in parent.parents):
        return False
    if relative.as_posix() == "results/planner-v4/raw.jsonl":
        return False
    return True


def selected_contents(root=ROOT, strict=True):
    root = Path(root).resolve()
    files = []
    for name in FILE_PATHS:
        candidate = root / name
        if approved_file(candidate, root):
            files.append(candidate)
    for name in TREE_PATHS:
        directory = root / name
        if directory.is_dir() and not directory.is_symlink():
            files.extend(path for path in directory.rglob("*") if approved_file(path, root))
    contents = {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(set(files))}
    contents[".gitignore"] = IGNORE_CONTENT.encode()
    if strict:
        missing = [name for name in REQUIRED_PATHS if name not in contents]
        if missing:
            raise ValueError("missing required public files: " + ", ".join(missing))
        manifest = json.loads(contents["evidence/frozen-v0.3/manifest.json"])
        for name, expected in manifest["evidence_hashes"].items():
            if name not in contents or hashlib.sha256(contents[name]).hexdigest() != expected:
                raise ValueError("missing or changed frozen evidence: " + name)
        for name, expected in manifest["source_hashes"].items():
            archived = "evidence/frozen-v0.3/" + name
            if archived not in contents or hashlib.sha256(contents[archived]).hexdigest() != expected:
                raise ValueError("missing or changed archived source: " + name)
    return contents


def inspect_contents(contents):
    """Reject private context and obvious credentials without printing their values."""
    findings = []
    for name, payload in contents.items():
        if name.endswith(".gz"):
            try:
                payload = gzip.decompress(payload)
            except (OSError, EOFError) as error:
                raise ValueError("invalid compressed artifact: " + name) from error
        lower = (name + "\n" + payload.decode("utf-8", errors="replace")).lower()
        if any(token in lower for token in PROHIBITED_CONTEXT):
            findings.append(name + " (private context)")
        text = payload.decode("utf-8", errors="replace")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            findings.append(name + " (private locator or credential pattern)")
    if findings:
        raise ValueError("public export blocked; review: " + ", ".join(sorted(set(findings))))


def export_public(output, root=ROOT, strict=True):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("output exists; choose a fresh directory")
    if output == root or root.is_relative_to(output):
        raise ValueError("output cannot contain the source root")
    for name in TREE_PATHS:
        if output.is_relative_to(root / name):
            raise ValueError("output must be outside allowlisted source directories")
    contents = selected_contents(root, strict=strict)
    inspect_contents(contents)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".eiv-public-", dir=output.parent))
    try:
        for name, payload in contents.items():
            destination = temporary / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        manifest = {"schema": "eiv-public-export-1", "files": {
            name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(contents.items())}}
        (temporary / "PUBLIC-MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        # rename has no overwrite behavior here: destination existence is checked
        # immediately before committing the prepared complete directory.
        if output.exists():
            raise ValueError("output appeared during export; existing files preserved")
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {"path": str(output), "files": len(contents),
            "manifest_sha256": hashlib.sha256((output / "PUBLIC-MANIFEST.json").read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--zip", dest="archive", type=Path,
                        help="Also create a deterministic source ZIP; must not exist")
    args = parser.parse_args()
    if args.archive is not None and args.archive.exists():
        parser.error("ZIP exists; choose a fresh path")
    result = export_public(args.output)
    if args.archive is not None:
        sys.path.insert(0, str(ROOT))
        from scripts.package_release import create_bundle
        result["archive"] = create_bundle(args.archive, root=args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
