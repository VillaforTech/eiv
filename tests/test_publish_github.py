"""Publication guards and offline planning; no remote mutation is performed."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.publish_github import (
    CommandError, PublishError, Runner, SETTINGS, TOPICS, MATERIALIZED_EVIDENCE_PATHS, configure, configure_protection, execute,
    fresh_commit, require_empty, require_public, validate_repository,
)


PUBLIC = {"full_name": "VillaforTech/eiv", "private": False, "visibility": "public", "permissions": {"admin": True}}


class PublicationTests(unittest.TestCase):
    def test_default_plan_is_offline_and_has_no_writes(self):
        runner = Mock()
        result = execute("VillaforTech/eiv", Path("missing-export"), runner=runner)
        self.assertEqual(result["status"], "planned")
        self.assertEqual((result["network_calls"], result["files_written"]), (0, 0))
        self.assertEqual(runner.mock_calls, [])

    def test_repository_validation_rejects_urls_options_and_shell_text(self):
        for value in ("https://github.com/owner/repo", "--public/repo", "owner/repo;touch bad", "owner/../../private"):
            with self.subTest(value=value), self.assertRaises(PublishError):
                validate_repository(value)
        self.assertEqual(validate_repository("VillaforTech/eiv"), "VillaforTech/eiv")

    def test_private_and_nonadmin_targets_are_never_converted(self):
        for metadata in (dict(PUBLIC, private=True), dict(PUBLIC, visibility="private"),
                         dict(PUBLIC, permissions={"admin": False}), dict(PUBLIC, archived=True), dict(PUBLIC, fork=True)):
            with self.subTest(metadata=metadata), self.assertRaises(PublishError):
                require_public(metadata, "VillaforTech/eiv")

    def test_existing_refs_prevent_publication(self):
        runner = Mock()
        runner.run.return_value = "abcdef\trefs/tags/v1\n"
        with self.assertRaisesRegex(PublishError, "existing refs"):
            require_empty(runner, "VillaforTech/eiv")
        self.assertEqual(runner.run.call_args.args[0][:3], ["git", "ls-remote", "--refs"])

    def test_private_repo_apply_fails_before_remote_mutation(self):
        runner = Mock()
        runner.api.return_value = dict(PUBLIC, private=True)
        with patch("scripts.publish_github.clean_payloads", return_value={"README.md": b"public"}):
            result = execute("VillaforTech/eiv", Path("export"), apply=True, runner=runner)
        self.assertEqual(result["status"], "failed")
        runner.run.assert_not_called()
        self.assertEqual(runner.api.call_count, 1)

    def test_populated_repo_apply_fails_without_push(self):
        runner = Mock()
        runner.api.return_value = PUBLIC
        runner.run.return_value = "abcdef\trefs/heads/main\n"
        with patch("scripts.publish_github.clean_payloads", return_value={"README.md": b"public"}):
            result = execute("VillaforTech/eiv", Path("export"), apply=True, runner=runner)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(runner.run.call_count, 1)

    def test_configure_only_never_loads_source_or_pushes(self):
        runner = Mock()
        runner.api.return_value = PUBLIC
        with patch("scripts.publish_github.clean_payloads") as load, patch("scripts.publish_github.configure") as configure:
            result = execute("VillaforTech/eiv", Path("absent"), apply=True, configure_only=True, runner=runner)
        self.assertEqual(result["status"], "complete")
        load.assert_not_called()
        runner.run.assert_not_called()
        configure.assert_called_once()

    def test_runner_uses_argv_no_shell_and_suppresses_error_output(self):
        process = subprocess.CompletedProcess([], 1, "secret stdout", "secret stderr HTTP 403")
        with patch("scripts.publish_github.subprocess.run", return_value=process) as call:
            with self.assertRaises(CommandError) as caught:
                Runner().run(["gh", "api", "user"])
        self.assertFalse(call.call_args.kwargs["shell"])
        self.assertEqual(call.call_args.args[0], ["gh", "api", "user"])
        self.assertNotIn("secret", str(caught.exception))
        self.assertEqual(caught.exception.status, 403)

    def test_api_json_payload_goes_through_stdin(self):
        runner = Runner()
        with patch.object(runner, "run", return_value='{"ok":true}') as call:
            self.assertEqual(runner.api("repos/owner/repo", "PATCH", {"has_issues": True}), {"ok": True})
        argv = call.call_args.args[0]
        self.assertIn("--input", argv)
        self.assertEqual(json.loads(call.call_args.kwargs["stdin"]), {"has_issues": True})

    def test_fresh_commit_has_one_root_and_no_inherited_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            sha = fresh_commit(Runner(), work, {"README.md": b"Independent public root\n"},
                               {"login": "example", "id": 123, "name": None})
            self.assertEqual(len(sha), 40)
            result = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=work, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), "1")
            self.assertFalse((work / ".git/refs/remotes").exists())

    def test_fresh_commit_tracks_distribution_but_preserves_ignored_materialized_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            payloads = {
                "README.md": b"Public research source\n",
                ".gitignore": ("\n".join("/" + path for path in sorted(MATERIALIZED_EVIDENCE_PATHS)) + "\n").encode(),
                "PUBLIC-MANIFEST.json": b'{"schema":"eiv-public-export-1","files":{}}\n',
                "evidence/distribution/manifest.json": b'{"schema":"test-fixture"}\n',
                "evidence/distribution/fixture.gz.part-01": b"compressed-distribution-fixture",
                **{path: b"materialized evidence fixture\n" for path in MATERIALIZED_EVIDENCE_PATHS},
            }
            fresh_commit(Runner(), work, payloads, {"login": "example", "id": 123})
            tracked = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=work, text=True).splitlines())
            self.assertEqual(tracked, set(payloads) - MATERIALIZED_EVIDENCE_PATHS)
            for path in MATERIALIZED_EVIDENCE_PATHS:
                self.assertEqual((work / path).read_bytes(), payloads[path])
            self.assertEqual(subprocess.check_output(["git", "status", "--porcelain"], cwd=work, text=True), "")

    def test_protection_is_deferred_until_ci_success(self):
        runner = Mock()
        runner.api.side_effect = [{"sha": "a" * 40}, {"workflow_runs": []}]
        receipt = {"steps": []}
        configure_protection(runner, "VillaforTech/eiv", receipt)
        self.assertEqual(receipt["steps"][0]["status"], "deferred")
        self.assertEqual(runner.api.call_count, 2)

    def test_configuration_protects_the_actual_default_branch_including_slashes(self):
        for branch, encoded in (("master", "master"), ("release/v0.4", "release%2Fv0.4")):
            with self.subTest(branch=branch):
                calls = []
                sha = "a" * 40
                base = "repos/VillaforTech/eiv"
                def api(endpoint, method="GET", body=None):
                    calls.append((endpoint, method))
                    if endpoint == base:
                        return dict(PUBLIC, default_branch=branch, **SETTINGS)
                    if endpoint == base + "/topics":
                        return {"names": TOPICS}
                    if endpoint.rsplit("/", 1)[-1] in {"private-vulnerability-reporting", "vulnerability-alerts", "automated-security-fixes"}:
                        return {"enabled": True}
                    if endpoint == base + "/commits/" + encoded:
                        return {"sha": sha}
                    if endpoint == base + f"/actions/runs?head_sha={sha}&per_page=100":
                        return {"workflow_runs": [{"id": 1, "head_sha": sha,
                            "path": ".github/workflows/ci.yml", "status": "completed",
                            "conclusion": "success", "check_suite_id": 10}]}
                    if endpoint == base + f"/commits/{sha}/check-runs?per_page=100":
                        return {"total_count": 1, "check_runs": [{"name": "test", "status": "completed",
                            "conclusion": "success", "check_suite": {"id": 10},
                            "app": {"slug": "github-actions"}}]}
                    if endpoint == base + "/branches/" + encoded + "/protection":
                        if method == "GET":
                            raise CommandError("gh", 1, 404)
                        return body
                    self.fail("unexpected endpoint: " + endpoint)
                runner = Mock()
                runner.api.side_effect = api
                receipt = {"steps": []}
                configure(runner, "VillaforTech/eiv", receipt)
                self.assertEqual(receipt["steps"][-1]["status"], "verified")
                self.assertEqual(receipt["steps"][-1]["branch"], branch)
                self.assertIn((base + "/branches/" + encoded + "/protection", "PUT"), calls)
                self.assertNotIn((base + "/commits/main", "GET"), calls)

    def test_protection_uses_observed_checks_zero_reviewers_and_no_force(self):
        sha = "a" * 40
        run = {"id": 1, "head_sha": sha, "path": ".github/workflows/ci.yml", "status": "completed", "conclusion": "success", "check_suite_id": 10}
        checks = {"total_count": 1, "check_runs": [{"name": "observed-test", "status": "completed", "conclusion": "success", "check_suite": {"id": 10}, "app": {"slug": "github-actions"}}]}
        runner = Mock()
        runner.api.side_effect = [{"sha": sha}, {"workflow_runs": [run]}, checks,
                                  CommandError("gh", 1, 404), {"required_status_checks": {"contexts": ["observed-test"], "strict": True}, "enforce_admins": {"enabled": True}, "required_linear_history": {"enabled": True}, "allow_force_pushes": {"enabled": False}, "allow_deletions": {"enabled": False}, "required_conversation_resolution": {"enabled": True}, "required_pull_request_reviews": {"required_approving_review_count": 0, "require_code_owner_reviews": False, "require_last_push_approval": False}}]
        receipt = {"steps": []}
        configure_protection(runner, "VillaforTech/eiv", receipt)
        policy = runner.api.call_args.args[2]
        self.assertEqual(policy["required_status_checks"]["contexts"], ["observed-test"])
        self.assertEqual(policy["required_pull_request_reviews"]["required_approving_review_count"], 0)
        self.assertFalse(policy["allow_force_pushes"])
        self.assertFalse(policy["allow_deletions"])
        self.assertTrue(policy["required_conversation_resolution"])
        self.assertEqual(receipt["steps"][-1]["status"], "verified")


if __name__ == "__main__":
    unittest.main()
