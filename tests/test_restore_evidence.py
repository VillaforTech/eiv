"""Local-only recovery preserves frozen data and never replaces conflicting bytes."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.restore_evidence import EXPECTED, ROOT, restore_evidence


class EvidenceRestorationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / 'evidence/distribution', self.root / 'evidence/distribution')
        manifest = {'schema': 'eiv-public-export-1', 'files': {
            item['path']: item['sha256'] for item in EXPECTED['files']}}
        (self.root / 'PUBLIC-MANIFEST.json').write_text(json.dumps(manifest))

    def assert_no_targets(self):
        self.assertTrue(all(not (self.root / item['path']).exists() for item in EXPECTED['files']))

    def test_exact_restoration_matches_every_frozen_hash_and_size(self):
        result = restore_evidence(self.root)
        self.assertEqual(result['verified_files'], 3)
        self.assertEqual(set(result['restored']), {item['path'] for item in EXPECTED['files']})
        for item in EXPECTED['files']:
            data = (self.root / item['path']).read_bytes()
            self.assertEqual(len(data), item['size'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])

    def test_repeat_is_idempotent_and_preserves_existing_modification_times(self):
        restore_evidence(self.root)
        before = {item['path']: (self.root / item['path']).stat().st_mtime_ns for item in EXPECTED['files']}
        result = restore_evidence(self.root)
        self.assertEqual(result['restored'], [])
        self.assertEqual(len(result['already_present']), 3)
        self.assertEqual(before, {item['path']: (self.root / item['path']).stat().st_mtime_ns for item in EXPECTED['files']})

    def test_conflicting_existing_file_is_preserved_and_no_missing_target_written(self):
        item = EXPECTED['files'][-1]
        target = self.root / item['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'existing evidence must be preserved')
        with self.assertRaises(ValueError):
            restore_evidence(self.root)
        self.assertEqual(target.read_bytes(), b'existing evidence must be preserved')
        self.assertTrue(all(not (self.root / other['path']).exists() for other in EXPECTED['files'][:-1]))

    def test_missing_or_corrupt_final_compressed_part_rejects_before_any_write(self):
        part = self.root / EXPECTED['files'][-1]['gzip_parts'][-1]['path']
        original = part.read_bytes()
        for payload in (None, bytes([original[0] ^ 1]) + original[1:]):
            with self.subTest(missing=payload is None):
                if payload is None:
                    part.unlink()
                else:
                    part.write_bytes(payload)
                with self.assertRaises(ValueError):
                    restore_evidence(self.root)
                self.assert_no_targets()
                part.write_bytes(original)

    def test_metadata_cannot_substitute_different_expected_hashes(self):
        for relative in ('PUBLIC-MANIFEST.json', 'evidence/distribution/manifest.json'):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                data = json.loads(original)
                if relative == 'PUBLIC-MANIFEST.json':
                    data['files'][EXPECTED['files'][0]['path']] = '0' * 64
                else:
                    data['files'][0]['sha256'] = '0' * 64
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    restore_evidence(self.root)
                self.assert_no_targets()
                path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
