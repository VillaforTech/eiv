"""Publish an explicitly requested release after the CI dependency jobs pass.

Runs only on a default-branch push in the intended GitHub Actions repository.
No request file means no network calls. Existing tags/assets are never replaced.
A new release stays a draft until its source ZIP and checksum have uploaded.
An interrupted existing draft fails visibly for review instead of modifying it.

References:
https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
https://docs.github.com/en/rest/releases/releases#create-a-release
https://docs.github.com/en/rest/releases/assets#upload-a-release-asset
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.package_release import create_bundle

REPOSITORY = "VillaforTech/eiv"
API = "https://api.github.com"


class ReleaseError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a bearer token to a redirected destination.


class GitHubAPI:
    def __init__(self, token):
        if not token:
            raise ReleaseError("GITHUB_TOKEN is required")
        self.token = token
        self.opener = build_opener(NoRedirect())

    def request(self, path, method="GET", data=None, *, missing_ok=False,
                content_type="application/json"):
        url = API + path if path.startswith("/") else path
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc not in {"api.github.com", "uploads.github.com"}:
            raise ReleaseError("refusing a non-GitHub API destination")
        if missing_ok and method != "GET":
            raise ReleaseError("only explicit read lookups may return absent")
        payload = json.dumps(data).encode() if isinstance(data, dict) else data
        request = Request(url, data=payload, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "Content-Type": content_type,
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "eiv-release-workflow",
        })
        try:
            with self.opener.open(request, timeout=120) as response:
                body = response.read()
                return json.loads(body) if body else None
        except HTTPError as error:
            if error.code == 404 and missing_ok:
                return None
            raise ReleaseError(f"GitHub {method} failed with HTTP {error.code}; response body suppressed") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ReleaseError("GitHub request failed; no missing-resource inference was made") from error


def _require(condition, message):
    if not condition:
        raise ReleaseError(message)


def read_request(path):
    path = Path(path)
    if not path.exists():
        return None
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4096,
             "release request must be a small regular JSON file")
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            _require(key not in obj, "release request contains duplicate keys")
            obj[key] = value
        return obj
    try:
        request = json.loads(path.read_text(), object_pairs_hook=unique)
    except (ValueError, OSError) as error:
        raise ReleaseError("invalid release request JSON") from error
    _require(isinstance(request, dict) and set(request) == {"version"}
             and isinstance(request["version"], str)
             and re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", request["version"]),
             "release request must contain one numeric version")
    return request


def tag_target(api, base, tag):
    reference = api.request(base + "/git/ref/tags/" + quote(tag, safe=""), missing_ok=True)
    if reference is None:
        return None
    _require(reference.get("ref") == "refs/tags/" + tag, "tag lookup returned a different reference")
    obj = reference["object"]
    for _ in range(8):
        if obj.get("type") == "commit":
            return obj["sha"]
        _require(obj.get("type") == "tag", "tag does not point to a commit")
        obj = api.request(base + "/git/tags/" + obj["sha"])["object"]
    raise ReleaseError("annotated tag chain exceeds the release bound")


def publish(request, environment, api, root=ROOT):
    """Apply one version request; callers supply an authenticated API transport."""
    root = Path(root)
    _require(environment.get("GITHUB_ACTIONS") == "true"
             and environment.get("GITHUB_EVENT_NAME") == "push"
             and environment.get("GITHUB_REPOSITORY") == REPOSITORY,
             "release publication requires a push workflow in the intended repository")
    sha = environment.get("GITHUB_SHA", "")
    _require(re.fullmatch(r"[0-9a-f]{40}", sha), "GITHUB_SHA must identify one exact commit")
    version = request["version"]
    tag = "v" + version
    notes_path = root / "docs" / ("release-" + tag + ".md")
    _require(notes_path.is_file() and not notes_path.is_symlink(), "release notes are required")
    notes = notes_path.read_text()
    _require(bool(notes.strip()) and len(notes) <= 100000, "release notes must be nonempty and bounded")
    package_version = re.search(r'^version\s*=\s*"([^"]+)"\s*$',
                                (root / "pyproject.toml").read_text(), re.MULTILINE)
    _require(package_version and package_version.group(1) == version, "request version differs from package version")
    base = "/repos/" + REPOSITORY
    repository = api.request(base)
    _require(repository.get("full_name", "").lower() == REPOSITORY.lower()
             and repository.get("private") is False
             and not repository.get("archived") and not repository.get("fork"),
             "release target must be the intended public, active, non-fork repository")
    branch = repository["default_branch"]
    _require(environment.get("GITHUB_REF") == "refs/heads/" + branch,
             "release publication requires the current default branch")
    head = api.request(base + "/commits/" + quote(branch, safe=""))
    _require(head.get("sha") == sha, "default branch advanced; refusing a stale release request")
    target = tag_target(api, base, tag)
    _require(target in {None, sha}, "existing tag targets another commit; it will not be moved")
    existing = api.request(base + "/releases/tags/" + quote(tag, safe=""), missing_ok=True)
    if existing is not None:
        _require(target == sha and existing.get("tag_name") == tag,
                 "existing release has an unverified or different target")
        _require(existing.get("draft") is False,
                 "existing draft preserved; inspect the interrupted publication before retrying")
        return {"status": "unchanged", "tag": tag, "commit": sha, "url": existing["html_url"]}
    # Assemble all local assets before any remote write. package_release also
    # checks the public allowlist and records the bytes of every bundled file.
    with tempfile.TemporaryDirectory(prefix="eiv-release-") as temporary:
        archive = Path(temporary) / ("eiv-" + version + "-source.zip")
        create_bundle(archive, root=root)
        assets = [(archive, "application/zip"), (archive.with_suffix(".sha256"), "text/plain")]
        release = api.request(base + "/releases", "POST", {
            "tag_name": tag, "target_commitish": sha, "name": "EIV " + version,
            "body": notes, "draft": True, "prerelease": False,
        })
        _require(release.get("tag_name") == tag and release.get("draft") is True,
                 "created draft differs from requested release")
        release_id = release["id"]
        _require(type(release_id) is int and release_id > 0, "invalid release identifier")
        upload = release["upload_url"].split("{", 1)[0]
        expected_upload = f"https://uploads.github.com/repos/{REPOSITORY}/releases/{release_id}/assets"
        _require(upload == expected_upload, "unexpected release upload destination")
        for path, media_type in assets:
            payload = path.read_bytes()
            uploaded = api.request(upload + "?" + urlencode({"name": path.name}), "POST", payload,
                                   content_type=media_type)
            _require(uploaded.get("name") == path.name and uploaded.get("state") == "uploaded"
                     and uploaded.get("size") == len(payload), "release asset upload was not verified")
            digest = uploaded.get("digest")
            _require(digest in {None, "sha256:" + hashlib.sha256(payload).hexdigest()},
                     "release asset digest mismatch")
        # Recheck the mutable branch/tag immediately before publishing the draft.
        _require(api.request(base + "/commits/" + quote(branch, safe="")).get("sha") == sha,
                 "default branch advanced; uploaded draft remains unpublished")
        _require(tag_target(api, base, tag) in {None, sha},
                 "tag changed during upload; draft remains unpublished")
        completed = api.request(base + "/releases/" + str(release_id), "PATCH", {"draft": False})
        _require(completed.get("draft") is False and completed.get("tag_name") == tag,
                 "release publication could not be verified")
        _require(tag_target(api, base, tag) == sha, "published release tag does not match the verified commit")
        return {"status": "published", "tag": tag, "commit": sha,
                "url": completed["html_url"], "assets": [p.name for p, _ in assets]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, default=ROOT / ".github/release-request.json")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    try:
        request = read_request(args.request)
        if request is None:
            result = {"status": "skipped", "reason": "no release request"}
        elif not args.publish:
            result = {"status": "planned", "tag": "v" + request["version"], "network_calls": 0}
        else:
            result = publish(request, os.environ, GitHubAPI(os.environ.get("GITHUB_TOKEN")))
    except (ReleaseError, OSError, KeyError, TypeError) as error:
        parser.exit(1, "Release failed: " + str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
