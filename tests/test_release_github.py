"""Offline release guards: no tag replacement or credential-bearing live calls."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from scripts.release_github import GitHubAPI, REPOSITORY, ReleaseError, publish, read_request

SHA = "a" * 40
ENV = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": REPOSITORY,
       "GITHUB_REF": "refs/heads/master", "GITHUB_SHA": SHA}
BASE = "/repos/" + REPOSITORY


class FakeAPI:
    def __init__(self, *, target=None, existing=None, branch="master", head=SHA, fail_upload=False):
        self.target, self.existing = target, existing
        self.branch, self.head, self.fail_upload = branch, head, fail_upload
        self.calls = []

    def request(self, path, method="GET", data=None, **kwargs):
        self.calls.append((path, method, data))
        if method == "GET":
            if path == BASE:
                return {"full_name": REPOSITORY, "private": False, "default_branch": self.branch}
            if "/commits/" in path:
                return {"sha": self.head}
            if "/git/ref/tags/" in path:
                return None if self.target is None else {"ref": "refs/tags/v0.4.0", "object": {"type": "commit", "sha": self.target}}
            if "/releases/tags/" in path:
                return self.existing
        if path == BASE + "/releases" and method == "POST":
            return {"id": 12, "tag_name": "v0.4.0", "draft": True,
                    "upload_url": f"https://uploads.github.com/repos/{REPOSITORY}/releases/12/assets{{?name,label}}"}
        if path.startswith("https://uploads.github.com/"):
            if self.fail_upload:
                raise ReleaseError("upload failed")
            return {"name": parse_qs(urlsplit(path).query)["name"][0], "state": "uploaded",
                    "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
        if path == BASE + "/releases/12" and method == "PATCH":
            self.target = SHA
            return {"tag_name": "v0.4.0", "draft": False, "html_url": "https://github.com/" + REPOSITORY + "/releases/tag/v0.4.0"}
        raise AssertionError((path, method))


def bundle(path, root):
    path.write_bytes(b"deterministic source fixture")
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n")


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/release-v0.4.0.md").write_text("Release notes.\n")
        (self.root / "pyproject.toml").write_text('[project]\nversion = "0.4.0"\n')
        self.request = {"version": "0.4.0"}

    def tearDown(self):
        self.temporary.cleanup()

    def test_missing_request_skips_and_malformed_versions_fail(self):
        path = self.root / "request.json"
        self.assertIsNone(read_request(path))
        for payload in ('{"version":"0.4.0","version":"0.5.0"}',
                        '{"version":"../other"}', '{"version":"v0.4.0"}',
                        '{"version":"0.4.0","publish":true}', '[]'):
            path.write_text(payload)
            with self.subTest(payload=payload), self.assertRaises(ReleaseError):
                read_request(path)
        path.write_text(json.dumps(self.request))
        self.assertEqual(read_request(path), self.request)

    def test_http_missing_is_only_explicit_get_404(self):
        client = GitHubAPI("test-token-not-a-real-credential")
        for code in (401, 403, 429, 500, 502):
            client.opener = Mock()
            client.opener.open.side_effect = HTTPError("https://api.github.com/x", code, "error", {}, io.BytesIO(b"private response"))
            with self.subTest(code=code), self.assertRaises(ReleaseError) as error:
                client.request("/x", missing_ok=True)
            self.assertNotIn("private response", str(error.exception))
        client.opener.open.side_effect = HTTPError("https://api.github.com/x", 404, "absent", {}, io.BytesIO())
        self.assertIsNone(client.request("/x", missing_ok=True))
        with self.assertRaises(ReleaseError):
            client.request("/x")
        client.opener.open.side_effect = URLError("network failed")
        with self.assertRaises(ReleaseError):
            client.request("/x", missing_ok=True)

    def test_token_is_never_sent_to_an_unexpected_host(self):
        client = GitHubAPI("test-token-not-a-real-credential")
        client.opener = Mock()
        for destination in ("https://example.com/x", "http://api.github.com/x", "https://api.github.com@example.com/x"):
            with self.assertRaises(ReleaseError):
                client.request(destination)
        client.opener.open.assert_not_called()

    def test_wrong_context_fails_before_network(self):
        for changes in ({"GITHUB_EVENT_NAME": "pull_request"}, {"GITHUB_REPOSITORY": "someone/fork"},
                        {"GITHUB_ACTIONS": "false"}, {"GITHUB_SHA": "master"}):
            api = Mock()
            with self.subTest(changes=changes), self.assertRaises(ReleaseError):
                publish(self.request, dict(ENV, **changes), api, self.root)
            api.request.assert_not_called()

    def test_nondefault_branch_and_stale_commit_never_write(self):
        for api, env in ((FakeAPI(head="b" * 40), ENV), (FakeAPI(), dict(ENV, GITHUB_REF="refs/heads/feature"))):
            with self.assertRaises(ReleaseError):
                publish(self.request, env, api, self.root)
            self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_existing_tag_at_different_commit_is_never_moved(self):
        api = FakeAPI(target="b" * 40)
        with self.assertRaisesRegex(ReleaseError, "will not be moved"):
            publish(self.request, ENV, api, self.root)
        self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_existing_same_commit_release_is_unchanged(self):
        api = FakeAPI(target=SHA, existing={"tag_name": "v0.4.0", "draft": False, "html_url": "existing-url"})
        result = publish(self.request, ENV, api, self.root)
        self.assertEqual(result["status"], "unchanged")
        self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_existing_draft_is_preserved_for_review(self):
        api = FakeAPI(target=SHA, existing={"tag_name": "v0.4.0", "draft": True})
        with self.assertRaisesRegex(ReleaseError, "draft preserved"):
            publish(self.request, ENV, api, self.root)
        self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_draft_uploads_then_publishes_exact_verified_commit(self):
        api = FakeAPI()
        with patch("scripts.release_github.create_bundle", side_effect=bundle):
            result = publish(self.request, ENV, api, self.root)
        self.assertEqual((result["status"], result["commit"]), ("published", SHA))
        writes = [(path, method, data) for path, method, data in api.calls if method != "GET"]
        self.assertEqual([method for _, method, _ in writes], ["POST", "POST", "POST", "PATCH"])
        self.assertEqual(writes[0][2]["target_commitish"], SHA)
        self.assertTrue(writes[0][2]["draft"])
        self.assertEqual(writes[-1][2], {"draft": False})
        self.assertEqual(result["assets"], ["eiv-0.4.0-source.zip", "eiv-0.4.0-source.sha256"])

    def test_failed_asset_upload_never_publishes_or_deletes_draft(self):
        api = FakeAPI(fail_upload=True)
        with patch("scripts.release_github.create_bundle", side_effect=bundle):
            with self.assertRaisesRegex(ReleaseError, "upload failed"):
                publish(self.request, ENV, api, self.root)
        self.assertFalse(any(method in {"PATCH", "DELETE"} for _, method, _ in api.calls))

    def test_package_version_mismatch_fails_before_network(self):
        (self.root / "pyproject.toml").write_text('[project]\nversion = "0.5.0"\n')
        api = Mock()
        with self.assertRaisesRegex(ReleaseError, "version differs"):
            publish(self.request, ENV, api, self.root)
        api.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
