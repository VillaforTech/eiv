# Reproducibility

First restore the three compressed historical data files, then run the current
test suite and historical source-isolated replay:

```sh
python3 scripts/restore_evidence.py
python3 scripts/reproduce.py --output build/reproduction-unique
```

The restoration command is offline and idempotent: it validates compressed and
uncompressed sizes and hashes, and refuses to replace conflicting local bytes.
The [distribution record](../evidence/distribution/README.md) lists the exact files.
`PUBLIC-MANIFEST.json` describes the materialized source export, including these
restored files. Source release ZIPs include them already.

The replay command refuses an existing output directory. No model inference, external
action or paid service is invoked. Historical sources are archived in
`evidence/frozen-v0.3/` with a manifest that binds exact code and evidence bytes.
The replay runner stages those files in a temporary workspace, clears inherited
Python import paths and executes them with the current interpreter.

It verifies original v1/v2/v3 freezes, the legacy fixtures, all 240 v2 outcomes
and aggregate metrics (excluding timing fields), saved pilot analysis and
original pilot source hashes, byte-identical v3 outputs (28,800 rows), and the
independent selection audit. Historical freeze hashes are unchanged. Current
code changes are validated separately by the current tests.

To run only historical replay:

```sh
python3 scripts/replay_frozen.py --output build/historical-unique
```

To reproduce the new, explicitly post-hoc planner comparison:

```sh
python3 -m eiv_experiment.planner --output build/planner-unique
```

This comparison reuses already exposed synthetic cases and a known
counterexample. It tests implementation/mechanism behavior, not generalization.

## Restricted execution environments

Some managed hosts prohibit opening even loopback sockets. In that environment,
use `--skip-http-tests` with `scripts/reproduce.py` to run the remaining suite
and full historical replay. This excludes `tests/test_web.py` explicitly and
records `complete_test_suite_run: false`; it is not a full test pass. Socket-free
hardening tests still exercise the real HTTP parser. The CI configuration runs
the full suite on a standard runner; configuration alone is not a CI receipt.

## Interpreting receipts

A successful replay establishes consistency with the files in this checkout.
Hashes do not authenticate the author. Synthetic labels have not been reviewed
by humans, and repeated outcome counts are not independent observations. Saved
model analysis does not mean a new model was run. Read the research report for
validity limits before citing a headline number.
