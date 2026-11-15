# Project completion record

Version 0.4.0 · 14 November 2026 · Roberto Villafuerte

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

GitHub Actions run `43654509468` passed all seven jobs for source commit
`b81067777b20adf26e2403bac87d14f9fffdda00`, tested through pull-request merge
commit `b4e3d5b5a359814a9cfee6989fd447dd28929733`: the full **176-test** suite
on Python 3.10, 3.11, 3.12, 3.13 and 3.14, package installation outside the
checkout, historical/planner replay, and four JavaScript portfolio tests.
The Python total includes 164 core/release checks and 12 publication-helper
checks. All five Python job logs explicitly report 176 tests and `OK`, including
live HTTP integration. The [validation receipt](../evidence/current-validation.json)
records the run, tested commits, job IDs and log verification. The changes were
merged as `0481a478227fb72e9ea2d63175fd97c6d3c672a5`.

The local managed host could not bind loopback sockets. The latest local retry
completed 169 tests, but the HTTP test class could not start because socket
binding was denied. The local full-suite command therefore failed at setup;
successful CI includes those seven HTTP tests and closed that execution gap. Browser visual inspection remains unperformed:
the local browser runtime was unavailable and headless Chrome was blocked.
Responsive styles, semantic markup, keyboard controls, labels and relative
links were checked statically; those checks do not replace a rendered review.

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

The portfolio remains a draft, intended for integration into the author's
website. Review destination URLs and hosting configuration before publication.
A public source export contains only the allowlisted personal-project files,
without repository history or private administrative material. Its creation
does not itself publish a repository or website.
