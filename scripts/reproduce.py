"""Check current software and replay archived historical evidence offline.

Use a new output directory. Frozen v0.3 source is isolated from current code;
neither benchmark records nor original freeze hashes are silently rewritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.replay_frozen import run_replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--skip-http-tests", action="store_true",
                        help="Explicitly exclude localhost integration tests on restricted hosts; recorded as incomplete validation")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("choose a fresh output directory; existing evidence is preserved")
    output.mkdir(parents=True)
    environment = dict(os.environ, PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    if args.skip_http_tests:
        command = ["-c", "import sys,unittest; sys.path.insert(0,'tests'); names=[p.stem for p in __import__('pathlib').Path('tests').glob('test_*.py') if p.name != 'test_web.py']; result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(sorted(names))); sys.exit(not result.wasSuccessful())"]
    else:
        command = ["-m", "unittest", "discover", "-s", "tests", "-v"]
    tests = subprocess.run([sys.executable, *command], cwd=ROOT, env=environment, capture_output=True, text=True)
    (output / "tests.txt").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("current software tests failed; inspect " + str(output / "tests.txt"))
    historical = run_replay(output / "historical", ROOT)
    report = {
        "python": platform.python_version(),
        "current_tests_exit_code": tests.returncode,
        "http_integration_tests": "explicitly excluded; not validated" if args.skip_http_tests else "included",
        "complete_test_suite_run": not args.skip_http_tests,
        "current_source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ("eiv", "eiv_experiment", "eiv_llm", "tests", "scripts")
            for path in sorted((ROOT / directory).glob("*.py"))
        },
        "historical_replay": historical,
        "scope": "Current engineering checks plus exact archived software replay; no claim of human semantic validation or production safety.",
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
