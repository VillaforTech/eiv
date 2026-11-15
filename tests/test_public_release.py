"""Historical source isolation and fail-closed evidence-integrity regressions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.replay_frozen import ARCHIVE, ROOT, run_replay, safe_relative, verified_payloads


def sha(content):
    return hashlib.sha256(content).hexdigest()


class FrozenReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ARCHIVE / "eiv").mkdir(parents=True)
        (self.root / "results").mkdir()
        (self.root / ARCHIVE / "eiv/core.py").write_bytes(b"FROZEN = True\n")
        (self.root / "results/raw.json").write_bytes(b"{}\n")
        self.manifest = {
            "schema": "eiv-frozen-replay-1",
            "source_hashes": {"eiv/core.py": sha(b"FROZEN = True\n")},
            "evidence_hashes": {"results/raw.json": sha(b"{}\n")},
        }
        self.save()

    def save(self):
        (self.root / ARCHIVE / "manifest.json").write_text(json.dumps(self.manifest))

    def test_frozen_sources_are_independent_of_live_modules(self):
        (self.root / "eiv").mkdir()
        (self.root / "eiv/core.py").write_text("FROZEN = False\n")
        _, payloads = verified_payloads(self.root)
        self.assertEqual(payloads["eiv/core.py"], b"FROZEN = True\n")

    def test_corrupt_evidence_is_rejected_before_execution_or_output_creation(self):
        (self.root / "results/raw.json").write_text('{"changed": true}')
        output = self.root / "new-output"
        with self.assertRaisesRegex(ValueError, "evidence_hashes mismatch"):
            run_replay(output, self.root)
        self.assertFalse(output.exists())

    def test_unlisted_executable_cannot_enter_historical_workspace(self):
        (self.root / ARCHIVE / "eiv/injected.py").write_text("raise RuntimeError()")
        with self.assertRaisesRegex(ValueError, "executable source"):
            verified_payloads(self.root)

    def test_source_corruption_and_source_evidence_collisions_rejected(self):
        self.manifest["source_hashes"]["eiv/core.py"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "source_hashes mismatch"):
            verified_payloads(self.root)
        self.manifest["source_hashes"]["eiv/core.py"] = sha(b"FROZEN = True\n")
        self.manifest["evidence_hashes"]["eiv/core.py"] = sha(b"FROZEN = True\n")
        self.save()
        with self.assertRaisesRegex(ValueError, "collision"):
            verified_payloads(self.root)

    def test_unsafe_paths_and_existing_output_rejected(self):
        for name in ("../outside.py", "/absolute.py", "folder\\outside.py", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_relative(name)
        with self.assertRaisesRegex(ValueError, "output exists"):
            run_replay(self.root, self.root)

    def test_actual_archive_matches_original_v3_freeze(self):
        _, payloads = verified_payloads(ROOT)
        original = json.loads(payloads["benchmark/v3/manifest.json"])
        for name, expected in original["source_hashes"].items():
            self.assertEqual(sha(payloads[name]), expected, name)


if __name__ == "__main__":
    unittest.main()
