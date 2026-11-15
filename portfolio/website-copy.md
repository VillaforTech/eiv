# EIV — website copy

Draft for Roberto Villafuerte's personal portfolio. Intended path:
`/projects/eiv`. The live repository URL is a publication-time field; use a
verified destination when deploying. The draft page uses relative source links.

## Project card

**EIV — Interactive Verifiable Specification**

A formal permission workbench for agent design. EIV represents a requested
action explicitly, checks candidate meanings, plans clarifying questions, and
exports a replayable record of the inputs, answers, checks, and decision.
It studies a subtle failure: a correct verifier can still authorize the wrong
action when the user's intended meaning is missing.

**Tags:** AI safety · formal methods · interactive systems · Python · research engineering

**Role:** Independent project by Roberto Villafuerte

**Actions:** Explore the experiment · Read the research · Source code

## Case-study opening

### Verified consequences. Unverified intent.

An agent can check a permission perfectly—and still misunderstand what you meant.

EIV makes that gap inspectable. It models the operation, resource, recipient,
scope, and relevant facts; compares what possible interpretations permit; and
records how a user's clarification changes the decision.

Before a system can verify an action, someone has to decide what the instruction
means. If the intended meaning never enters the set of interpretations, every
subsequent check can agree on the wrong answer.

The intended application is a conversational agent with an inspectable permission
layer. The implemented project is a local research workbench, CLI, and Python
core with finite permissions and simulated actions. General chat and real tool
enforcement remain separate integration work. The current result is a working
research artifact, controlled comparisons, and explicit counterexamples.

## What was built in v0.4

| Component | Concrete implementation |
| --- | --- |
| Formal evaluator | Exhaustive finite checking with explicit entailment, refutation, inconsistency, underdetermination, and resource-limit outcomes. |
| Action model | A typed request for domain, action, resource, recipient, and scope; Boolean facts; candidate allow/deny policies; bounded question partitions. |
| Input boundary | Strict JSON validation and a narrow controlled-English adapter; unsupported prose abstains. |
| Clarification | First relevant question, greedy pair separation, and an exact bounded planner. Answers restrict the existing candidate set; `other` and `unsure` abstain. |
| Exact planning | Memoized decision-tree search maximizing resolved supplied hypotheses within a budget, then minimizing summed question count. Equal candidate weights are counts, not human-intent probabilities. |
| Workbench and CLI | Real Python-backed local interaction, examples, question-strategy selection, candidate checks, and JSON export. |
| Session integrity | Posted state is revalidated and decisions recomputed; client-cached decisions are not trusted. The case digest is a checksum, not a permission token. |
| Research infrastructure | Frozen source-isolated replay, a saved local-model pilot, independent calculation audits, and a separately labeled post-hoc planner comparison. |
| Distribution | Packaged runtime assets, MIT license, citation metadata, contributor guidance, and automated checks. |

The exact planner stops when additional questioning cannot improve its declared
finite objective. Search-limit exhaustion produces abstention; it does not
approximate permission or recover interpretations missing from the candidate set.

The workbench and scientific replay use Python's standard library. They do not
execute file or message actions, and the documented replay requires no model or
paid service.

## What the action trace actually records

For a proposed action such as sending `report` to `Alex` once, an exported session
contains the original instruction, the explicit request, supplied facts, candidate
policies, permission-dimension and condition checks, formal outcomes, and reason
codes. A clarification records the selected question, answer ID, and candidate IDs
before and after restriction. The final result includes its decision, remaining
candidates, question counts, and explicit simulated/unverified-coverage flags.

This makes the connection between a represented instruction, a user response,
and a decision inspectable. It does not prove that the representation captures
the user's true intent. The record contains observable inputs and computed
checks, not hidden model reasoning. It is neither a signed capability nor an
execution receipt. See [the formal action model](../docs/formal-action-model.md).

## What the evidence says

In a constructed V3 slice with complete interpretation coverage and one question,
targeted selection correctly resolves 288/288 outcomes; ordinary-first resolves
96/288. With a three-question budget, both reach 288/288, using 288 and 576
questions respectively.

The strongest limitation appears in the same experiment. Remove all restrictive
interpretations and both policies falsely authorize 144/144 latent-deny cases.
Wrong consensus prevents clarification.

These are exact finite counts, not real-world rates. V3 consists of 1,440
AI-authored constructed cases and 28,800 correlated outcome records across
policies, orders, and budgets. Six scenarios share one Boolean structure, and
the semantic labels lack independent human review.

The repository also preserves unfavorable evidence. V2 reduces questions from
40 to 25 while adding four false allows and four false denials. A separate
eight-intent counterexample shows that the pair-separation score is not generally
budget-optimal: it resolves 0/8 intents with one question, while the first-question
comparator resolves 1/8. Neither makes an incorrect resolved decision there.

The v0.4 exact planner addresses that known selection limitation: it resolves
1/8 of the same intents at budget one, compared with greedy 0/8, and avoids
fruitless follow-up questions at larger budgets. This is a **post-hoc engineering
correction**, not a held-out comparison. The new experiment contains 17,280
outcomes over already-inspected cases. It retains the omitted-meaning failure:
all three policies falsely allow 144/144 latent-deny cases after restrictive
readings are removed in the budget-one slice.

## Engineering validation

The v0.4.0 release passed 194 Python tests on each version from 3.10 through 3.14, including live HTTP
integration. Package installation is checked outside the source checkout.
The exact planner agrees with an independent reference on 564 small policy
problems. Historical replay audits all 240 V2 and 28,800 V3 outcomes without new
model inference; four local JavaScript tests cover the separate website
illustration. These are implementation and reproducibility checks, not evidence
of real-world safety. See the [validation receipt](../evidence/current-validation.json)
and [completion record](../docs/project-status.md).

## Why it is useful

The project makes a normally hidden engineering boundary concrete. A reviewer can
inspect the candidates, facts, selected question, and finite reasoning behind a
decision. A contributor can reproduce an observed failure before changing the
method. A practitioner can see why more formal checking does not automatically
repair missing intent.

The benefit is inspectability and reproducibility. Superior real-world safety,
human usability, and general natural-language understanding remain unestablished.

## Path from the workbench to a conversational agent

The current artifact supplies a bounded permission-reasoning component. A future
chat adapter could propose structured cases and present clarifications, but its
semantic coverage would need independent evaluation. A future executor would
need authenticated approvals, a separately designed enforcement boundary,
revocation, replay protection, action-state revalidation, and execution receipts.
None of those production capabilities is implied by a simulated `allow` result.

The next empirical work is independent human semantic review, prospectively
frozen cases, and user studies of question usefulness and cost. These questions
remain open even when every software test passes.

## Compact CV / portfolio achievement drafts

- Built EIV, a Python research workbench that formalizes proposed agent actions,
  compares candidate permissions, and exports replayable clarification and
  decision records; v0.4.0 validated with 194 automated tests on each Python version from 3.10 through 3.14.
- Implemented exact bounded clarification planning with memoized decision-tree
  search; checked it against an independent reference on 564 finite problems
  and documented a post-hoc correction to a known greedy-selection failure.
- Built reproducible evaluation and independent auditing for 28,800 frozen V3
  outcomes, preserving negative results and distinguishing formal correctness
  from interpretation coverage.

Use one or two bullets according to available space. Do not describe the system
as a production agent, claim deployment that has not occurred, or turn finite
benchmark counts into real-world safety rates.

## Intellectual context

Interactive semantic parsing already maintains interpretations and asks for
feedback [1]. nl2spec supports interactive translation of natural-language
requirements into formal specifications [2]. Work on ambiguity resolution
explicitly studies recovering omitted readings [3]. EIV adapts these established
ideas to a bounded permission experiment and makes its assumptions and negative
results visible. It does not claim priority for combining them.

1. Ziyu Yao, Yu Su, Huan Sun, and Wen-tau Yih. 2019. [Model-based Interactive Semantic Parsing: A Unified Framework and A Text-to-SQL Case Study](https://aclanthology.org/D19-1547/). EMNLP-IJCNLP. DOI: 10.18653/v1/D19-1547.
2. Matthias Cosler, Christopher Hahn, Daniel Mendoza, Frederik Schmitt, and Caroline Trippel. 2023. [nl2spec: Interactively Translating Unstructured Natural Language to Temporal Logics with Large Language Models](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18). CAV. DOI: 10.1007/978-3-031-37703-7_18.
3. Irina Saparina and Mirella Lapata. 2025. [Disambiguate First, Parse Later: Generating Interpretations for Ambiguity Resolution in Semantic Parsing](https://aclanthology.org/2025.findings-acl.863/). Findings ACL. DOI: 10.18653/v1/2025.findings-acl.863.

## Short Spanish project card

**EIV — Especificación Interactiva Verificable**

Un proyecto personal de investigación e ingeniería para modelar los permisos de
un agente de IA. EIV representa explícitamente la acción solicitada, compara
interpretaciones, verifica sus consecuencias y planifica aclaraciones. Cada
decisión conserva un registro de entradas, comprobaciones, respuestas y cambios
en las interpretaciones activas. La versión 0.4 incluye planificación exacta
acotada; v0.4.0 se validó con 194 pruebas automatizadas por versión de Python 3.10–3.14.

El objetivo es aportar una base verificable para agentes conversacionales.
Actualmente es un laboratorio local con acciones simuladas: no ejecuta
herramientas ni garantiza haber capturado la intención real del usuario.

**Logro breve:** Desarrollé un laboratorio de permisos para agentes con modelo
formal de acciones, planificación exacta de aclaraciones y decisiones
reproducibles; v0.4.0 se validó con 194 pruebas por versión de Python y auditorías de evidencia experimental.

**Etiquetas:** Seguridad de IA · métodos formales · sistemas interactivos · Python

## Metadata

- **Title:** EIV — Verified consequences. Unverified intent.
- **Description:** EIV models an agent's requested action, checks candidate permissions, plans clarification, and exports auditable decision records. A reproducible research project by Roberto Villafuerte.
- **Author:** Roberto Villafuerte
- **Intended repository:** `https://github.com/VillaforTech/eiv` — verify availability before publication.
- **Status:** Website draft; research-engineering artifact; simulated actions only.
