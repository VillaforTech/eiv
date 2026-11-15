# EIV · Interactive Verifiable Specification

[![Verify EIV](https://github.com/VillaforTech/eiv/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/VillaforTech/eiv/actions/workflows/ci.yml) · [Source](https://github.com/VillaforTech/eiv) · [Issues](https://github.com/VillaforTech/eiv/issues) · [MIT license](LICENSE)

**Verify what an instruction permits. Ask when interpretations disagree. Make the limits inspectable.**

A personal research-engineering project by **Roberto Villafuerte**. EIV turns a
bounded permission instruction into explicit candidate policies, checks the
consequences of each, and selects clarifying questions under a finite budget.
It makes a difficult boundary executable: **a correct verifier can still approve
the wrong action when the intended interpretation is missing.**

[Download v0.4.0](https://github.com/VillaforTech/eiv/releases/tag/v0.4.0) · [Research report](docs/research-report.md) · [Project page draft](portfolio/index.html) ·
[Personal website preview](portfolio/villafortech-preview.html) ·
[Formal action model](docs/formal-action-model.md) · [Architecture](docs/architecture.md) · [Usage and API](docs/usage.md) ·
[Historical evidence](results/dimensions-v3/analysis.md) · [Planner comparison](results/planner-v4/analysis.md) · [Academic references](research/references.bib)

## Why this project exists

An agent asked to “send the report to Alex or Bea” must decide what “or” permits,
which recipient is authorized, and whether more information is needed. EIV
separates semantic assumptions from formal consequences. Every candidate,
clarification, filtering step and decision remains inspectable in JSON.

The practical advantages are explicit assumptions, selective clarification,
deterministic replay, and useful counterexamples. EIV is a research simulator:
it does not execute actions or constitute a production authorization system.

## A formal model beside the agent

The intended architecture gives an agent an explicit action contract: represent
the proposed operation, check it against candidate policies and trusted facts,
then record why the system asks, allows, denies or abstains. The trace exposes
the instruction, candidate meanings, checks, clarifications and final decision.
This makes the assumptions behind a proposed action reviewable.

The current implementation provides that **decision and trace layer for simulated
file and message permissions**. Chat integration, signed authorization tokens
and real action execution are future work, with a separate security design.
A trace documents represented intent and formal consequences; it cannot prove
that the actual human intention was included. Read the
[formal action model](docs/formal-action-model.md) for the worked example and
contribution roadmap.

## What is implemented

- A bounded finite-model evaluator with explicit entailment, refutation,
  inconsistency, underdetermination and resource-limit outcomes.
- Structured file/message permission policies and a narrow controlled-English
  adapter. Unknown semantics and unresolved conditions cause abstention.
- Three question strategies: first relevant question, greedy disagreement score,
  and an **exact bounded planner** that maximizes resolved supplied hypotheses
  within a budget, then minimizes their total question count.
- A local browser workbench backed by the actual Python engine, with candidate
  inspection, clarification, downloadable traces and adversarial examples.
- A packaged CLI, strict JSON boundaries, bounded computation and HTTP resources,
  regression tests, frozen scientific replay, and independent result auditing.
- A static portfolio draft with an educational interactive demonstration, a
  research report, verified academic references and citation metadata.

“Exact” refers to a declared finite planning objective with equal candidate
weights. Those weights are not probabilities of real human intent. Planning
cannot recover a meaning that the candidate set omitted.

## Try it

Requires Python 3.10+. Runtime and scientific replay use the standard library.

```sh
git clone https://github.com/VillaforTech/eiv.git
cd eiv
python3 scripts/restore_evidence.py
python3 -m unittest discover -s tests -v
python3 -m eiv.web
```

Open **http://127.0.0.1:8765**. Start with recipient ambiguity, answer a question,
then try the omitted-interpretation and selector-counterexample examples.
Choose the exact planner to compare it with the historical greedy strategy.

```sh
python3 -m eiv interpret 'You may send report to alex or bea once.' \
  --domain messages --action send --resource report --recipient alex \
  --strategy optimal --max-questions 1

python3 -m eiv authorize examples/permission-case.json \
  --answer interpretation=c2 --strategy optimal
```

Optional installation from this checkout (build tools may be downloaded by pip):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/eiv --help
.venv/bin/eiv-workbench
```

The installed package includes workbench assets and examples. Full experiments
require the source checkout and its frozen data. No model download, inference,
API key, cloud account or paid service is required.

## Evidence, including the failures

| Study | Observed result | What it supports |
|---|---|---|
| Historical v2, 40 synthetic test cases | EIV and conventional each resolve 28/40 correctly. EIV asks 25 vs 40 questions but adds 4 false allows and 4 false denials. | A negative efficiency/error tradeoff, not a safety improvement. |
| Saved Gemma 2 9B pilot, 10 cases | EIV is correct on 7/10; one candidate per case and zero questions. | Structured-output feasibility; not evidence for clarification effectiveness. |
| Historical v3, complete coverage, budget 1 | Targeted resolves 288/288 vs 96/288 for ordinary-first. | A constructed mechanism diagnostic. |
| Historical v3, complete coverage, budget 3 | Both resolve 288/288, using 288 vs 576 questions. | Question ordering affects interaction cost in this finite design. |
| Historical v3, restrictive readings omitted | Both questioning policies falsely allow all 144 latent-deny cases. | Wrong consensus suppresses clarification. |
| Known selector counterexample, budget 1 | Greedy resolves 0/8; the new exact planner resolves 1/8. | The new finite objective addresses a demonstrated greedy limitation. |

V3 contains **1,440 constructed cases and 28,800 repeated outcomes**. Six scenarios
share one Boolean structure. Orders and budgets are correlated, labels are
AI-authored and remain unreviewed by humans, and none of these counts measures
real-world error prevalence. The new planner evaluation is explicitly post hoc.

## Reproduce and inspect

The Git checkout stores three large historical data files as verified gzip parts.
Run `python3 scripts/restore_evidence.py` once after cloning to restore their exact
original bytes locally. It uses no network access and refuses conflicting files.
The release source ZIP includes the restored files. See the
[distribution record](evidence/distribution/README.md) for paths and hashes.

```sh
python3 scripts/restore_evidence.py
python3 scripts/reproduce.py --output build/reproduction-unique
python3 -m eiv_experiment.planner --output build/planner-comparison
```

Use fresh output directories. Historical replay uses archived source matching
its original hashes; current hardening never silently changes the historical
implementation or experimental evidence. See [reproducibility](docs/reproducibility.md).

| Location | Contents |
|---|---|
| `eiv/` | Finite evaluator, permission engine, exact planner, CLI and local API |
| `eiv_experiment/` | Engineering studies, replay and independent audit |
| `eiv_llm/` | Analysis and integrity checks for saved local-model output |
| `benchmark/`, `results/` | Versioned synthetic data, raw outcomes and summaries |
| `evidence/frozen-v0.3/` | Original source for isolated historical replay |
| `tests/` | Core, security, planning, transport and reproducibility regressions |
| `docs/`, `research/` | Architecture, API, limitations, report and references |
| `portfolio/` | Website draft; static presentation, not a deployed agent |

## Research grounding

The project draws on interactive semantic parsing (Yao et al., 2019),
clarification under ambiguity (Kuhn et al., 2023), and natural-language-to-formal
specification (Cosler et al., 2023). The contribution is an inspectable permission
case study and failure analysis, not a claim to invent interactive parsing or
formal verification. The [report](docs/research-report.md) maps each comparison
to a verified primary source and separates measured results from future work.

## Scope and next research

The bounded engineering project is implemented. Independent semantic review,
user studies, stronger candidate generation and prospective evaluation are
separate research work; their outcomes cannot be manufactured by more code.
See the [public roadmap](https://github.com/VillaforTech/eiv/issues) and the [completion record](docs/project-status.md) for completed work and open
empirical questions. Client replay data is never a permission token. Do not
expose the local development server publicly.

Released under the [MIT license](LICENSE). Use [CITATION.cff](CITATION.cff) to cite
this software and [references.bib](research/references.bib) for its academic
context. Contributions are welcome through [CONTRIBUTING.md](CONTRIBUTING.md).
