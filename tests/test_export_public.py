"""Public export omits private files and fails closed before publishing bytes."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.export_public import export_public, inspect_contents, selected_contents
from scripts.package_release import create_bundle


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        (self.root / "README.md").write_text("EIV public research")
        (self.root / "eiv").mkdir()
        (self.root / "eiv/core.py").write_text("value = 1\n")
        (self.root / "docs").mkdir()
        (self.root / "docs/private-notes.md").write_text("private notes")
        self.output = self.root.parent / "export"

    def test_allowlist_excludes_unknown_docs_caches_links_and_uncompressed_planner_trace(self):
        (self.root / "eiv/__pycache__").mkdir()
        (self.root / "eiv/__pycache__/cache.pyc").write_bytes(b"cache")
        (self.root / "eiv/link.py").symlink_to(self.root / "docs/private-notes.md")
        (self.root / "eiv/linked").symlink_to(self.root / "docs", target_is_directory=True)
        planner = self.root / "results/planner-v4"
        planner.mkdir(parents=True)
        (planner / "raw.jsonl").write_text("excluded large raw")
        (planner / "raw.jsonl.gz").write_bytes(gzip.compress(b"{}\n", mtime=0))
        contents = selected_contents(self.root, strict=False)
        self.assertEqual(set(contents), {"README.md", "eiv/core.py", ".gitignore", "results/planner-v4/raw.jsonl.gz"})

    def test_disallowed_context_blocks_before_creating_output(self):
        (self.root / "README.md").write_text("blue" + "dot")
        with self.assertRaisesRegex(ValueError, "private context"):
            export_public(self.output, self.root, strict=False)
        self.assertFalse(self.output.exists())

    def test_private_patterns_checked_inside_compressed_trace(self):
        private = ("/" + "Users" + "/example/Documents/private").encode()
        with self.assertRaisesRegex(ValueError, "private locator"):
            inspect_contents({"data.jsonl.gz": gzip.compress(private, mtime=0)})

    def test_export_is_deterministic_and_refuses_overwrite(self):
        first = export_public(self.output, self.root, strict=False)
        other = self.root.parent / "other"
        second = export_public(other, self.root, strict=False)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertFalse((self.output / "docs/private-notes.md").exists())
        with self.assertRaisesRegex(ValueError, "output exists"):
            export_public(self.output, self.root, strict=False)
        manifest = json.loads((self.output / "PUBLIC-MANIFEST.json").read_text())
        self.assertEqual(set(manifest["files"]), {"README.md", "eiv/core.py", ".gitignore"})

    def test_bundle_uses_same_allowlist_and_export_manifest(self):
        export_public(self.output, self.root, strict=False)
        target = self.root.parent / "source.zip"
        create_bundle(target, self.output)
        with zipfile.ZipFile(target) as bundle:
            self.assertIn("PUBLIC-MANIFEST.json", bundle.namelist())
            self.assertNotIn("docs/private-notes.md", bundle.namelist())
            self.assertIn("BUNDLE-MANIFEST.json", bundle.namelist())

    def test_export_rejects_incomplete_release_and_self_inclusion(self):
        with self.assertRaisesRegex(ValueError, "missing required"):
            export_public(self.output, self.root)
        with self.assertRaisesRegex(ValueError, "outside allowlisted"):
            export_public(self.root / "eiv/generated", self.root, strict=False)


if __name__ == "__main__":
    unittest.main()
