# Project completion record

Version 0.4.0 · 15 November 2026 · Roberto Villafuerte

## Completed engineering scope

| Area | Delivered |
|---|---|
| Core | Finite checking, permission dimensions, explicit ambiguity and abstention |
| Clarification | Historical first/greedy strategies plus exact bounded planning |
| Robustness | Shared expression/work budgets, strict session replay, JSON and HTTP bounds |
| Usability | Packaged CLI and local workbench with examples and trace export |
| Research | Historical source-isolated replay; new post-hoc planner comparison |
| Transparency | Negative results, coverage failure, counterexample and validity limits retained |
| Distribution | MIT license, citation metadata, contributor/security guidance, public export tooling |
| Presentation | Academic report, BibTeX and responsive static portfolio draft |
| Automation | CI passes on Python 3.10–3.14, including full HTTP tests, installation and replay |

## Validation completed

The public [GitHub Actions run 43660601749](https://github.com/VillaforTech/eiv/actions/runs/43660601749)
passed all eight jobs for exact source commit
`fb1e634133d9c0a1a9097c0b09ed74d25e3d6436`. All five Python job logs report
**194 tests and OK** on Python 3.10, 3.11, 3.12, 3.13 and 3.14, including live
HTTP integration and package installation outside the checkout. The suite includes
164 core/release checks, 14 publication-helper checks, 11 release guards and five
local evidence-restoration checks. Four JavaScript portfolio tests also pass.

The [validation receipt](../evidence/current-validation.json) records the public
run, exact commit, job IDs and verified log summaries. Local restoration checks
recover the three compressed evidence files byte for byte before tests and replay.
The release job in that validation run did not publish a release because no
version request was present; actual release publication is separately verified.

The release was originally prepared on a host without loopback binding or
browser review. The 2026-11-15 administrative/presentation follow-up used a fresh
public checkout on a host with working loopback: the full suite passed locally,
installation was checked outside the checkout, and the actual Python workbench
was exercised in a browser from recipient ambiguity to a simulated denial.
The website preview was reviewed over HTTP at desktop and 390px mobile widths,
including project/case navigation and absence of horizontal overflow. Release validation
counts above remain historical; the helper regression brings the current suite
to **195** tests.

Historical replay verifies 25 source files and 43 evidence files, including
all 240 v2 outcomes and all 28,800 v3 outcomes. V3 outputs and the independent
selection audit match exactly. Saved model analysis is reproduced without new
inference. The installed wheel was built and checked outside the repository:
UI assets load and the exact planner selects the expected counterexample
question.

The planner is compared to an independent reference over 564 small policy
problems. The new post-hoc experiment contains 17,280 outcomes, 96 counterexample
paths and 18 nonselecting-reply checks. Exact planning resolves the known
budget-one counterexample on 1/8 paths versus greedy 0/8; at larger budgets it
avoids fruitless follow-up questions. It preserves the omitted-meaning failure.

## Published release

[v0.4.0](https://github.com/VillaforTech/eiv/releases/tag/v0.4.0) is published
from exact commit `3b805d9caa157f11e668381c9cfaea2e595f88f5`, after all eight
jobs in [release CI](https://github.com/VillaforTech/eiv/actions/runs/43660978132)
succeeded. The attached ZIP contains 201 files, including restored historical
evidence; its SHA-256 matches an independently generated local source bundle.
See the [publication receipt](../evidence/publication.json) for the full digest
and verified settings. Repository visibility and source/release publication
are complete. Administrative controls were subsequently applied and read back;
see [repository configuration](open-source.md). The release tag and assets were
not replaced by that follow-up.

## Open research, not represented as finished

1. Independent human review of intended meanings, plausibility and omitted readings.
2. Independently authored, prospectively frozen evaluation cases.
3. User studies measuring question usefulness, response accuracy and interaction cost.
4. Stronger semantic candidate generation with independently measured coverage.
5. A separate security design before any integration that executes real actions.

These are empirical dependencies, not implementation tasks that can be declared
complete from generated code or synthetic labels. The current artifact is a
complete bounded research-engineering project with an explicit research agenda.

## Public presentation

The source project is public at [VillaforTech/eiv](https://github.com/VillaforTech/eiv),
with independent source history, MIT licensing, documentation and a contribution
roadmap. Its publication does not deploy the portfolio website. The website case
study remains a reviewed draft for integration into the author's site.

[Repository configuration](open-source.md) and its [receipt](../evidence/github-configuration-20261115.json)
record the verified description/topics, feature switches, sole-maintainer branch
policy, dependency alerts/fixes, private reporting and secret protection.
CodeQL setup succeeded and its [contextual review](../evidence/codeql-triage-20261115.md)
records 123 open high-severity CLI path findings, including 39 historical-source
findings. They remain visible; scanning success is not a clean-security claim.
Optional generic secret patterns are unavailable for this user-owned repository
under the documented eligibility. No paid service was enabled. Two alerts on the old build-only setuptools pin
are addressed by `84.2.1` in the correction PR; default-branch closure remains
pending merge and is recorded in the [dependency review](../evidence/dependency-review-20261115.json).
