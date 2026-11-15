# v3 data card: explicit dimension-only clarification

This separate dataset contains 1,440 AI-authored, exposed combinatorial cases:
six permission scenarios × eight finite policies × five conditions × six
question orders. The scenarios share the same small Boolean decision structure.
Repeated orders, policies and question budgets are correlated. These are not
1,440 independent observations or human-validated natural-language examples.

Each JSONL row has `case_id`, `family`, `condition`, `question_order`, a validated
`public` structured permission case, a private evaluation `oracle`,
`gold_decision`, and an exact initial candidate-coverage flag. The policy receives
only `public`, finite candidate checks, and its own answer history. The wrapper
owns labels and scores. Gold labels are generated from the primary latent
dimension; an independent finite-set test checks all 48 complete finite policies.

`public` enumerates possible policies and binary question partitions. It does
not test language-model candidate generation. One dimension changes the requested
authorization and two alter unrelated grants. Questions can reveal only their
own binary value; `other`/`unsure` terminate without selecting a candidate group.
No full-intent prose is disclosed. Candidate consensus can still be wrong when
restrictive/permissive policies were deliberately omitted.

`manifest.json` freezes exact bytes of `cases.jsonl`, the protocol, generator
module and finite core before the complete run. It records no human approval.
The generator is deterministic and requires Python's standard library only.

```sh
python3 scripts/replay_frozen.py --output build/new-historical-replay
```

Choose a fresh output directory. The completed reference result is
`results/dimensions-v3/`; source protocol is `research/protocol-v3.md`. This
dataset preserves v1/v2 and does not replace their evidence. The public release
archives the original implementation in `evidence/frozen-v0.3/`. The replay
command verifies its hashes and runs it in isolation from the current hardened
implementation. Original source freeze hashes are intentionally unchanged;
running the historical module's `--verify-only` directly against a changed core
will correctly report a source mismatch. Data and code use are governed by the
repository license.
