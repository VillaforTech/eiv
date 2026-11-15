"""Plan or publish a clean EIV export to a new public GitHub repository.

Default mode is offline and read-only. --apply is required for mutations.
Existing private or populated repositories are never converted or overwritten.
Use --apply --configure-only to retry metadata and protection after CI completes.

API reference: https://cli.github.com/manual/gh_api
Repository reference: https://docs.github.com/en/rest/repos/repos
Protection reference: https://docs.github.com/en/rest/branches/branch-protection
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.export_public import inspect_contents, selected_contents

DESCRIPTION = "Verifiable permissions and bounded clarification for AI agents: finite checking, exact planning, reproducible experiments."
TOPICS = ["ai-safety", "formal-methods", "ai-agents", "authorization", "clarification", "python", "reproducible-research"]
SETTINGS = {"description": DESCRIPTION, "has_issues": True, "has_discussions": True,
            "has_wiki": False, "has_projects": False, "allow_squash_merge": True,
            "allow_merge_commit": False, "allow_rebase_merge": False,
            "delete_branch_on_merge": True}


class PublishError(RuntimeError):
    pass


class CommandError(PublishError):
    def __init__(self, executable, code, status=None):
        self.status = status
        super().__init__(f"{executable} failed (exit {code}" + (f", HTTP {status}" if status else "") + "); command output suppressed")


class Runner:
    def run(self, argv, *, cwd=None, stdin=None):
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update({"GIT_TERMINAL_PROMPT": "0", "GH_PROMPT_DISABLED": "1", "GH_HOST": "github.com"})
        try:
            result = subprocess.run(list(argv), cwd=cwd, input=stdin, text=True,
                                    capture_output=True, shell=False, env=environment, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PublishError(f"{argv[0]} unavailable or timed out; no command output disclosed") from error
        if result.returncode:
            status = re.search(r"HTTP (\d{3})", result.stderr)
            raise CommandError(argv[0], result.returncode, int(status.group(1)) if status else None)
        return result.stdout

    def api(self, endpoint, method="GET", body=None):
        argv = ["gh", "api", "--hostname", "github.com", "--method", method,
                "-H", "Accept: application/vnd.github+json", endpoint]
        if body is not None:
            argv += ["--input", "-"]
        output = self.run(argv, stdin=json.dumps(body) if body is not None else None)
        return json.loads(output) if output.strip() else None


def validate_repository(repository):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository):
        raise PublishError("repository must be an explicit owner/name on github.com")
    return repository


def clean_payloads(source):
    source = Path(source).resolve()
    if (source / ".git").exists():
        raise PublishError("source contains Git history; create a clean public export first")
    manifest_path = source / "PUBLIC-MANIFEST.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise PublishError("source needs PUBLIC-MANIFEST.json from export_public.py")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "eiv-public-export-1":
        raise PublishError("unsupported public export manifest")
    contents = selected_contents(source, strict=True)
    if set(manifest.get("files", {})) != set(contents):
        raise PublishError("export manifest differs from the current public allowlist")
    for name, payload in contents.items():
        if hashlib.sha256(payload).hexdigest() != manifest["files"][name]:
            raise PublishError("export bytes changed: " + name)
    inspect_contents(contents)
    contents["PUBLIC-MANIFEST.json"] = manifest_path.read_bytes()
    return contents


def require_public(metadata, repository):
    if metadata.get("full_name", "").lower() != repository.lower():
        raise PublishError("repository identity mismatch")
    if metadata.get("private") is not False or metadata.get("visibility", "public") != "public":
        raise PublishError("existing repository is not public; visibility will not be changed")
    if metadata.get("archived") or metadata.get("disabled") or metadata.get("fork"):
        raise PublishError("archived, disabled or fork repositories are not publication targets")
    if not metadata.get("permissions", {}).get("admin"):
        raise PublishError("repository administrator permission is required")


def require_empty(runner, repository):
    output = runner.run(["git", "ls-remote", "--refs", f"https://github.com/{repository}.git"])
    if output.strip():
        raise PublishError("repository has existing refs; refusing to push. Use --configure-only for settings")


def fresh_commit(runner, work, payloads, identity):
    for name, payload in payloads.items():
        destination = work / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    hooks = work / "empty-hooks"
    hooks.mkdir()
    runner.run(["git", "init", "--initial-branch=main", "."], cwd=work)
    runner.run(["git", "config", "core.hooksPath", str(hooks)], cwd=work)
    runner.run(["git", "add", "--", *sorted(payloads)], cwd=work)
    login, user_id = identity["login"], identity["id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", login) or type(user_id) is not int:
        raise PublishError("authenticated GitHub identity is invalid")
    runner.run(["git", "-c", "user.name=" + (identity.get("name") or login),
                "-c", f"user.email={user_id}+{login}@users.noreply.github.com",
                "commit", "--no-gpg-sign", "-m", "Release EIV personal research project"], cwd=work)
    if runner.run(["git", "rev-list", "--count", "HEAD"], cwd=work).strip() != "1":
        raise PublishError("publication must have exactly one initial commit")
    if runner.run(["git", "log", "-1", "--format=%P"], cwd=work).strip():
        raise PublishError("initial publication commit must have no parent")
    sha = runner.run(["git", "rev-parse", "HEAD"], cwd=work).strip()
    if not re.fullmatch(r"[a-f0-9]{40,64}", sha):
        raise PublishError("invalid local commit identifier")
    return sha


def configure(runner, repository, receipt):
    base = "repos/" + repository
    current = runner.api(base)
    require_public(current, repository)
    updated = runner.api(base, "PATCH", SETTINGS)
    if any(updated.get(key) != value for key, value in SETTINGS.items()):
        raise PublishError("repository metadata update was not fully confirmed")
    receipt["steps"].append({"step": "metadata", "status": "verified"})
    existing = runner.api(base + "/topics").get("names", [])
    topics = sorted(set(existing) | set(TOPICS))
    if len(topics) > 20:
        raise PublishError("topic union exceeds GitHub limit; existing topics preserved")
    result = runner.api(base + "/topics", "PUT", {"names": topics})
    if set(result.get("names", [])) != set(topics):
        raise PublishError("repository topics update was not confirmed")
    receipt["steps"].append({"step": "topics", "status": "verified"})
    for endpoint in ("private-vulnerability-reporting", "vulnerability-alerts", "automated-security-fixes"):
        try:
            runner.api(base + "/" + endpoint, "PUT")
            result = runner.api(base + "/" + endpoint)
            if endpoint != "vulnerability-alerts" and (not isinstance(result, dict) or result.get("enabled") is not True):
                raise PublishError("setting readback is not enabled")
            receipt["steps"].append({"step": endpoint, "status": "verified"})
        except PublishError as error:
            receipt["steps"].append({"step": endpoint, "status": "unconfirmed", "reason": str(error)})
    configure_protection(runner, repository, receipt, branch=current.get("default_branch", "main"))


def configure_protection(runner, repository, receipt, branch="main"):
    base = "repos/" + repository
    try:
        if not isinstance(branch, str) or not branch:
            raise PublishError("repository default branch is missing")
        branch_path = quote(branch, safe="")
        commit = runner.api(base + "/commits/" + branch_path)
        sha = commit["sha"]
        runs = runner.api(base + f"/actions/runs?head_sha={sha}&per_page=100")
        matches = [run for run in runs.get("workflow_runs", [])
                   if run.get("head_sha") == sha and run.get("path") == ".github/workflows/ci.yml"]
        latest = max(matches, key=lambda run: (run["id"], run.get("run_attempt", 1))) if matches else None
        if not latest or latest.get("status") != "completed" or latest.get("conclusion") != "success":
            receipt["steps"].append({"step": "branch_protection", "status": "deferred", "branch": branch, "reason": "Wait for successful CI on the default branch, then rerun --apply --configure-only"})
            return
        checks = runner.api(base + f"/commits/{sha}/check-runs?per_page=100")
        if checks.get("total_count", 0) > 100:
            raise PublishError("too many checks for bounded inspection; protection not changed")
        observed = [check for check in checks.get("check_runs", [])
                    if check.get("check_suite", {}).get("id") == latest.get("check_suite_id")
                    and check.get("app", {}).get("slug") == "github-actions"]
        if not observed or any(check.get("status") != "completed" or check.get("conclusion") != "success" for check in observed):
            raise PublishError("successful workflow checks not fully observable; protection not changed")
        contexts = sorted({check["name"] for check in observed})
        # Do not overwrite an existing policy, which may be stricter or contain
        # organization-specific allowances not represented by this script.
        try:
            existing = runner.api(base + "/branches/" + branch_path + "/protection")
        except CommandError as error:
            if error.status != 404:
                raise
            existing = None
        if existing is not None:
            status = "verified_existing" if protection_matches(existing, contexts) else "preserved_existing"
            receipt["steps"].append({"step": "branch_protection", "status": status, "branch": branch, "reason": "Existing policy retained; inspect manually if changes are needed"})
            return
        policy = {"required_status_checks": {"strict": True, "contexts": contexts},
                  "enforce_admins": True, "required_pull_request_reviews": {
                      "dismiss_stale_reviews": True, "require_code_owner_reviews": False,
                      "required_approving_review_count": 0, "require_last_push_approval": False},
                  "restrictions": None, "required_linear_history": True,
                  "allow_force_pushes": False, "allow_deletions": False,
                  "required_conversation_resolution": True}
        applied = runner.api(base + "/branches/" + branch_path + "/protection", "PUT", policy)
        if not protection_matches(applied, contexts):
            raise PublishError("branch protection settings not fully confirmed after update")
        receipt["steps"].append({"step": "branch_protection", "status": "verified", "branch": branch, "required_checks": contexts})
    except (PublishError, KeyError, TypeError) as error:
        receipt["steps"].append({"step": "branch_protection", "status": "unconfirmed", "reason": str(error)})


def protection_matches(policy, contexts):
    def enabled(name):
        value = policy.get(name)
        return value.get("enabled") if isinstance(value, dict) else value
    checks = policy.get("required_status_checks") or {}
    reviews = policy.get("required_pull_request_reviews") or {}
    return (set(contexts) <= set(checks.get("contexts", [])) and checks.get("strict") is True
            and enabled("enforce_admins") is True and enabled("required_linear_history") is True
            and enabled("allow_force_pushes") is False and enabled("allow_deletions") is False
            and enabled("required_conversation_resolution") is True
            and reviews.get("required_approving_review_count") == 0
            and reviews.get("require_code_owner_reviews") is False
            and reviews.get("require_last_push_approval") is False)


def execute(repository, source, *, apply=False, configure_only=False, runner=None):
    validate_repository(repository)
    receipt = {"repository": repository, "url": "https://github.com/" + repository,
               "mode": "apply" if apply else "plan", "steps": [], "status": "planned"}
    if not apply:
        receipt.update({"network_calls": 0, "files_written": 0, "configure_only": configure_only,
                        "planned_settings": SETTINGS, "topics": TOPICS,
                        "publication": "Fresh history from verified public export; new or empty public repository only",
                        "protection": "After successful CI: observed check names, resolved conversations, no force pushes/deletions, zero reviewer approvals"})
        return receipt
    runner = runner or Runner()
    try:
        payloads = None if configure_only else clean_payloads(source)
        metadata = None
        try:
            metadata = runner.api("repos/" + repository)
        except CommandError as error:
            if error.status != 404:
                raise
        if metadata is None:
            if configure_only:
                raise PublishError("repository does not exist; configuration-only cannot create it")
            runner.run(["gh", "repo", "create", repository, "--public", "--description", DESCRIPTION])
            receipt["steps"].append({"step": "repository_create", "status": "created"})
            metadata = runner.api("repos/" + repository)
        require_public(metadata, repository)
        if not configure_only:
            require_empty(runner, repository)
            identity = runner.api("user")
            with tempfile.TemporaryDirectory(prefix="eiv-publication-") as temporary:
                work = Path(temporary)
                sha = fresh_commit(runner, work, payloads, identity)
                runner.run(["git", "remote", "add", "origin", f"https://github.com/{repository}.git"], cwd=work)
                require_empty(runner, repository)
                # Fixed helper command uses gh's existing authentication without
                # displaying credentials or changing global Git configuration.
                runner.run(["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                            "push", "origin", "main:refs/heads/main"], cwd=work)
                receipt["steps"].append({"step": "initial_push", "status": "pushed", "sha": sha})
                remote = runner.api("repos/" + repository + "/commits/main")
                if remote.get("sha") != sha:
                    raise PublishError("remote main did not match the published commit")
                runner.api("repos/" + repository, "PATCH", {"default_branch": "main"})
        configure(runner, repository, receipt)
        receipt["status"] = "complete" if all(step["status"] not in {"deferred", "unconfirmed", "preserved_existing"} for step in receipt["steps"]) else "partial"
    except (PublishError, ValueError, OSError, KeyError, TypeError) as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
        receipt["retry"] = "If the initial push succeeded, rerun with --apply --configure-only. Never republish a populated repository."
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source", type=Path, default=ROOT / "build/public-eiv")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Offline read-only plan (default)")
    mode.add_argument("--apply", action="store_true", help="Explicitly apply remote publication/settings")
    parser.add_argument("--configure-only", action="store_true", help="Retry settings on an existing public repository; never push")
    args = parser.parse_args(argv)
    try:
        receipt = execute(args.repository, args.source, apply=args.apply, configure_only=args.configure_only)
    except PublishError as error:
        parser.error(str(error))
    print(json.dumps(receipt, indent=2))
    return 1 if receipt["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
