# Governance

EIV is an independently maintained research-engineering project. Roberto
Villafuerte is the initial maintainer. The MIT license permits others to use,
modify, redistribute and fork the software.

## Decisions

Small corrections can go directly to a pull request. Changes to permission
semantics, the planning objective, evidence handling or the execution boundary
start with a design issue describing the problem, alternatives, assumptions,
validation and migration impact. The maintainer decides after considering the
technical evidence and records the reason in the issue or pull request.

A merge requires relevant tests and reproducibility checks to pass. Frozen
results are immutable; a new method gets a new versioned experiment. Negative
findings are first-class project results. A contribution does not imply that
its author endorses all project claims.

## Roles and review

Anyone may open an issue or propose a change. The initial maintainer handles
triage, releases and security reports. Additional maintainers can be proposed
publicly after sustained, constructive contributions and careful review.
No outside reviewers, advisors or institutional endorsements are implied.

The initial single-maintainer workflow requires CI and resolved conversations;
it does not demand an unavailable second approver. Independent review is sought
for changes to core semantics and any future action-execution boundary.

## Releases

A release identifies the code revision, license, supported Python versions,
validation results, known limitations and artifact hashes. Release descriptions
separate implemented behavior from research proposals. A version tag alone is
not evidence of production readiness or independent scientific validation.

The project currently has no paid service, support contract or maintenance SLA.
Contributors retain attribution; cite academic sources and respect their
licenses. Participation follows the [code of conduct](CODE_OF_CONDUCT.md).
