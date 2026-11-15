"""Restore exact frozen research data locally from verified compressed parts.

Standard-library only. No network, remote service, subprocess, Git command,
credential access or permission operation is performed.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {'schema': 'eiv-evidence-distribution-1', 'files': [{'path': 'results/dimensions-v3/raw.jsonl', 'size': 23221296, 'sha256': '31faad7e4086ba6c2c32d73f2bbb199877ba293c98ab2880cb79383feeb2be4b', 'git_blob_sha1': '03069d82d5d683e5de9334f8350b54cc38fc10a5', 'gzip_size': 253404, 'gzip_sha256': 'b5004c659619e49fd9b7ab1391811bafb1feeb8248f804dc6be28947baede77c', 'gzip_parts': [{'path': 'evidence/distribution/v3-outcomes.jsonl.gz.part-01', 'size': 180000, 'sha256': '0997f8fde04b199edb830b0b5d9ad2f4a5d02bb55b7b0c11676c6d807a055674'}, {'path': 'evidence/distribution/v3-outcomes.jsonl.gz.part-02', 'size': 73404, 'sha256': '42b6b1caaf2f0c84b5fd492644c947c4bf3db9eb169ade0d8ddb03ff40267073'}]}, {'path': 'benchmark/v3/cases.jsonl', 'size': 6395904, 'sha256': '129fce5ea45f7bea2525457efab18e38a88ab9fd84118bd1e551fc26cd2b2600', 'git_blob_sha1': '0d1b94917e1b901a672cefbb6c9bcf409f31281f', 'gzip_size': 67637, 'gzip_sha256': '37c8b48623edbb5f301cdf6b2467fd595fd91bb70c4a7d1e16c198822ef2a418', 'gzip_parts': [{'path': 'evidence/distribution/v3-cases.jsonl.gz.part-01', 'size': 67637, 'sha256': '37c8b48623edbb5f301cdf6b2467fd595fd91bb70c4a7d1e16c198822ef2a418'}]}, {'path': 'results/engineering-v2/raw.jsonl', 'size': 1089023, 'sha256': 'adad3e8f2f40aeb90b1e8c84264ca974c0c6ab856fc8af8b626b0a8942194af2', 'git_blob_sha1': '445748653aebc3dda5f5f3a00b135ae3e86589f0', 'gzip_size': 19212, 'gzip_sha256': '12154eab7070cd558c86fd6db65d5e25cf96848015a60d6bb6b11a329caf5cbb', 'gzip_parts': [{'path': 'evidence/distribution/v2-outcomes.jsonl.gz.part-01', 'size': 19212, 'sha256': '12154eab7070cd558c86fd6db65d5e25cf96848015a60d6bb6b11a329caf5cbb'}]}]}


def restore_evidence(root=ROOT):
    """Verify every input before restoring missing files; preserve existing bytes."""
    root = Path(root).resolve()

    def target_path(relative):
        path = root / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents
                                    if parent != root and root in parent.parents):
            raise ValueError("symlink refused: " + relative)
        return path

    def read_regular(relative, expected_size=None):
        path = target_path(relative)
        if not path.is_file():
            raise ValueError("regular file required: " + relative)
        size = path.stat().st_size
        if expected_size is not None and size != expected_size:
            raise ValueError("size mismatch: " + relative)
        if expected_size is None and size > 1000000:
            raise ValueError("metadata size limit exceeded: " + relative)
        return path.read_bytes()

    def verify(data, size, expected, label):
        if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("size or SHA-256 mismatch: " + label)

    manifest = json.loads(read_regular("evidence/distribution/manifest.json"))
    if manifest != EXPECTED:
        raise ValueError("distribution metadata differs from fixed reviewed metadata")
    public = json.loads(read_regular("PUBLIC-MANIFEST.json"))
    if public.get("schema") != "eiv-public-export-1":
        raise ValueError("unexpected public source manifest")
    pending = []
    preserved = []
    for item in EXPECTED["files"]:
        if public["files"].get(item["path"]) != item["sha256"]:
            raise ValueError("public source manifest disagrees: " + item["path"])
        compressed = bytearray()
        for part in item["gzip_parts"]:
            data = read_regular(part["path"], part["size"])
            verify(data, part["size"], part["sha256"], part["path"])
            compressed.extend(data)
        verify(compressed, item["gzip_size"], item["gzip_sha256"], item["path"] + " compressed")
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
            data = stream.read(item["size"] + 1)
        verify(data, item["size"], item["sha256"], item["path"])
        git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if git_blob != item["git_blob_sha1"]:
            raise ValueError("content identifier mismatch: " + item["path"])
        target = target_path(item["path"])
        if target.exists():
            verify(read_regular(item["path"], item["size"]), item["size"], item["sha256"], item["path"] + " existing")
            preserved.append(item["path"])
        else:
            pending.append((item["path"], data))
    # All compressed parts and existing targets pass validation before writes.
    restored = []
    for relative, data in pending:
        target = target_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        restored.append(relative)
    return {"status": "verified", "restored": restored, "already_present": preserved,
            "verified_files": len(EXPECTED["files"]), "scope": "local evidence restoration only"}


if __name__ == "__main__":
    print(json.dumps(restore_evidence(), indent=2))
