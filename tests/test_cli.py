"""Strict JSON boundaries for the dependency-free command-line adapters."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eiv.__main__ import main


class CommandBoundaryTests(unittest.TestCase):
    def invoke_error(self, arguments):
        out, err = io.StringIO(), io.StringIO()
        with patch('sys.argv', ['eiv', *arguments]), redirect_stdout(out), redirect_stderr(err), \
                self.assertRaises(SystemExit) as stopped:
            main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertNotIn('Traceback', err.getvalue())
        return err.getvalue()

    def test_duplicate_facts_cannot_silently_select_the_permissive_value(self):
        error = self.invoke_error(['interpret', 'You may read report once if approved is true.',
                                   '--domain', 'files', '--action', 'read', '--resource', 'report',
                                   '--facts', '{"approved":false,"approved":true}'])
        self.assertIn('duplicate JSON key', error)

    def test_legacy_analyze_and_clarify_reject_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'case.json'
            path.write_text('{"title":"first","title":"second"}')
            for arguments in [['analyze', str(path)], ['clarify', str(path), 'q', 'yes']]:
                self.assertIn('duplicate JSON key', self.invoke_error(arguments))

    def test_nonobject_legacy_input_has_a_clean_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'case.json'
            for content in ['null', '1', 'true', '[]', '"text"']:
                path.write_text(content)
                self.assertIn('JSON object', self.invoke_error(['analyze', str(path)]))

    def test_invalid_utf8_is_a_clean_input_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'case.json'
            path.write_bytes(b'\xff')
            for command in ['analyze', 'authorize']:
                self.assertIn('error:', self.invoke_error([command, str(path)]))


if __name__ == '__main__':
    unittest.main()
