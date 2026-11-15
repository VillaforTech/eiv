# Contributing to EIV

Useful contributions expose a failure, improve a bounded guarantee, or make an
experiment easier to reproduce. Start with the README and
[research report](docs/research-report.md), [formal action model](docs/formal-action-model.md),
and [governance](GOVERNANCE.md).

1. Run `python3 -m unittest discover -s tests -v`.
2. Add a minimal case and a regression test for a behavioral change.
3. Keep latent intent and gold labels outside the policy interface.
4. Run `python3 scripts/reproduce.py --output build/reproduction-unique`.
5. For portfolio changes, run `node --test portfolio/test-demo.cjs`.
6. Describe the changed behavior, evidence, assumptions and limitations in your PR.

Do not replace frozen data, hashes, archived sources, or recorded negative
results. A new algorithm needs a new experiment/version, not rewritten history.
Never claim human review or model inference that did not take place. The
default runtime and replay use only the Python standard library.

The workbench is a local simulator. Changes that execute tools, use a paid
service, download models, or expose a network service need a separate design
and threat model. Do not add credentials or private transcripts to fixtures.

Report a defect with Python version, command, minimal synthetic input, expected
behavior and observed result. Respectful, specific discussion is expected.
