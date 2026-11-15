"""Release integrity regressions using tiny temporary source trees."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.package_release import create_bundle


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['README.md', 'pyproject.toml', 'requirements.lock', '.gitignore']:
            (self.root / name).write_text('sample ' + name)
        (self.root / 'eiv').mkdir()
        (self.root / 'eiv/core.py').write_text('original')
        self.target = self.root / 'dist/release.zip'

    def test_snapshot_hashes_written_bytes_despite_later_source_change(self):
        original = zipfile.ZipFile.writestr
        def mutate_then_write(bundle, *args, **kwargs):
            (self.root / 'eiv/core.py').write_text('changed during packaging')
            return original(bundle, *args, **kwargs)
        with patch.object(zipfile.ZipFile, 'writestr', mutate_then_write):
            create_bundle(self.target, self.root)
        with zipfile.ZipFile(self.target) as bundle:
            manifest = json.loads(bundle.read('BUNDLE-MANIFEST.json'))
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(bundle.read(name)).hexdigest(), digest)
            self.assertEqual(bundle.read('eiv/core.py'), b'original')

    def test_failure_leaves_current_release_and_success_preserves_previous(self):
        create_bundle(self.target, self.root)
        before = self.target.read_bytes()
        (self.root / 'eiv/core.py').write_text('second version')
        with patch.object(zipfile.ZipFile, 'writestr', side_effect=OSError('write interrupted')):
            with self.assertRaises(OSError):
                create_bundle(self.target, self.root)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(list(self.target.parent.glob('.release.zip-*')), [])
        create_bundle(self.target, self.root)
        digest = hashlib.sha256(before).hexdigest()[:12]
        self.assertEqual((self.target.parent / ('release-' + digest + '.zip')).read_bytes(), before)
        self.assertNotEqual(self.target.read_bytes(), before)

    def test_deterministic_content_and_reject_self_inclusion(self):
        first = create_bundle(self.target, self.root)
        second = create_bundle(self.root / 'dist/second.zip', self.root)
        self.assertEqual(first['sha256'], second['sha256'])
        with self.assertRaisesRegex(ValueError, 'outside bundled'):
            create_bundle(self.root / 'eiv/release.zip', self.root)


if __name__ == '__main__':
    unittest.main()
