# v3: dimension-only clarification mechanism study

Written on 23 October 2026 (America/Guayaquil), after exposure to v1/v2 and before
the new complete run. This is a separate deterministic engineering extension.
It preserves every old benchmark, prompt, raw result and pilot source. It is not
the gated confirmatory model/human study described in the v1/v2 protocols.

## Question, contribution and limits

Can a finite permission consequence guide selection among multiple bounded
clarifications when an answer reveals only the dimension actually asked? Does
this preserve abstention for explicit insufficient/outside answers? What happens
when every restrictive or permissive reading is absent?

The experiment constructs the structure needed to distinguish the algorithms;
it does not discover how often that structure occurs in real user instructions.
All inputs and labels are AI-authored, public to the implementer, programmatic,
and not reviewed by humans. Six permission scenarios share the same small
abstract Boolean decision structure. The rows are highly correlated variants,
orders and budgets, not thousands of independent examples. No LLM or human
participant is involved, and nothing executes a requested operation.

This fills a specific engineering gap in v2: multiple useful partitions and a
dimension-only answer channel. It cannot establish superiority over conventional
LLM clarification, natural-language interpretation quality, semantic coverage,
novelty, provider performance, practical safety or generalization.

## Finite authored inputs

Six permission scenarios vary the resource, action, recipient, duration,
condition or prohibition affecting one requested operation. Each scenario has
three binary dimensions and eight complete policies. One dimension determines
whether the requested symbolic operation is allowed; two modify unrelated
permissions while preserving that operation's consequence. The public input
includes all candidate policies that remain under the declared perturbation and
one predeclared binary partition per dimension that still has both alternatives.
It is an explicit structured-candidate task, not natural-language generation.

Cross all eight latent policies, all six question orders, and five conditions:

- **complete:** all eight policies are supplied, truthful dimension replies.
- **omit_restrictive:** remove every candidate denying the operation. This
  deliberately induces permissive consensus even for latent denial.
- **omit_permissive:** remove every candidate allowing the operation. This
  deliberately induces restrictive consensus even for latent permission.
- **unsure:** complete candidate coverage, but the first actually asked
  clarification receives `unsure` and terminates the interaction.
- **missing_latent_other:** remove exactly the latent policy, preserving seven
  candidates; the first actually asked clarification receives `other` and
  terminates. This models an explicit user rejection of the candidate space,
  not automatic detection of missing intent by the system.

There are 6 × 8 × 6 × 5 = **1,440 combinatorial cases**, each evaluated at
question budgets 0/1/2/3. Candidate IDs are opaque enumeration identifiers; the
policy never reads latent bits, the condition name, latent candidate ID, coverage
flag or gold label. In this tiny constructed space a researcher can infer these
properties, so label isolation is an interface property, not blinding.

## Oracle and information boundary

The orchestration code passes only the selected public question to the oracle.
For a truthful reply, the oracle looks up that dimension's latent Boolean value
and returns its public answer ID (`v0` or `v1`). It reveals no complete policy,
unasked dimensions, grant prose, hidden label or direct authorization decision.
The declared primary dimension's answer determines authorization by construction;
that is legitimate targeted disclosure, not uncharged full-intent access.

Every querying arm receives the identical answer to an identical question. A
normal reply discloses one selected binary value. Report both questions asked
and dimension-answer disclosures; `other`/`unsure` count as questions/replies
but reveal no selected binary value. No oracle is called at zero budget or after
candidate consensus. Missing-candidate stressors can therefore remain invisible.
`other`/`unsure` terminate with abstention; no regeneration or consent recovery is
permitted. The loop may only restrict the existing active candidate set.

## Arms and computation

All finite checks use the existing exhaustive evaluator, exactly once per public
case, and are shared across policies. Every policy receives the same candidates,
requests, facts, question partitions and finite outcomes. This isolates selection
and stopping behavior; it does not equalize LLM compute or actual wall-clock cost.

1. **direct:** allow/deny on unanimous candidate outcomes; otherwise abstain.
2. **ordinary_first:** consensus stopping plus the first remaining question with
   a positive number of separated unlike-decision candidate pairs. This matches
   the existing core's `question_strategy='first'` and is explicitly a fixed
   decision-aware engineering comparator, not a measurement of ordinary people
   or a capable conventional LLM.
3. **fixed_order:** consensus stopping plus the first remaining partition with
   at least two active nonempty answer groups, even with zero separated pairs.
4. **eiv_targeted:** consensus stopping plus the remaining question separating
   the greatest number of unlike-decision pairs, with declaration-order ties.
   This matches the original EIV core's targeted selection rule.
5. **abstain_all:** always abstain, never ask. This makes unresolved behavior
   visible instead of rewarding a trivial zero-false-authorization strategy.

The two first selectors may coincide in this design: nuisance partitions also
separate some unlike-decision pairs. Retain that null comparison explicitly.
Counterbalance all six question orders, so the primary dimension occurs first,
second and third equally. Relevant-first orders retain genuine ties. With the
maximum budget of three truthful questions, complete policies can be identified;
targeted questions are not required for eventual resolution in this space.

The study's `policy_step` takes only public inputs, verifier outcomes and answer
history. The benchmark/oracle wrapper owns labels and outcome scoring. Check
the new implementation against the original core for both targeted and first
selection on counterbalanced complete cases. Cache only finite candidate checks;
do not cache or share latent oracle information among policies.

## Outcomes and reporting

For every case/arm/budget preserve final decision, reason, active candidate IDs,
initial/retained exact candidate coverage, finite statuses, oracle answer IDs,
selected-question scores and the restriction trace. Report counts and rates:

| Measure | Numerator / denominator |
|---|---|
| False authorization | incorrect allow / latent-deny cases |
| False denial | incorrect deny / latent-allow cases |
| Correct resolved | correct allow-or-deny / all cases |
| Abstention | abstain / all cases |
| Selective accuracy | correct resolved / allow-or-deny outputs |
| Coverage | exact latent candidate present / all cases |
| Questions | total and distribution / all cases |
| Disclosure | selected binary answer count; nonselecting replies separately |

Stratify by budget, condition, scenario and primary-question position. Do not use
the 28,800 repeated outcome rows as independent evidence. No significance test,
bootstrap band, confidence/power claim or population estimate is justified by
exhausting this author-designed finite space. In particular, an aggregate across
arbitrary stressor frequencies has no naturalistic interpretation. Complete
coverage and missing-coverage outcomes must be reported separately.

The expected diagnostic pattern is shorter resolution for targeted selection
when the relevant dimension is later in declaration order; ties when it is
first; zero unresolved complete cases with three truthful questions; and wrong
consensus after wholesale permission-polarity omission. These are design
predictions, not positive empirical findings about models or users.

## Freeze, execution and resources

Before the full run, `python3 -m eiv_experiment.dimensions --prepare` creates the
new `benchmark/v3/` once. Its manifest records exact dataset bytes, this protocol,
the new module and existing finite core source hashes, plus preparation time.
`--verify-only` rejects changed data, code, protocol or deterministic generation.
An outcome run verifies the freeze first, rejects an existing output directory,
records the freeze checksum and source hashes before evaluation, and then saves
raw JSONL, all denominators, Markdown analysis and output hashes. Tests, manual
inspection and implementation authorship do not make the resulting set blind.

Reproduction uses Python's standard library, no network and no model inference.
External monetary spend is $0; local electricity, hardware and developer time are
unpriced. Freeze integrity proves bytes and internal reproducibility, not label
validity, independent authorship or trustworthy real-world facts.

Human review, independently authored policies, realistic oracle collection,
prospective model selection/budget and a genuinely new blinded evaluation remain
future research work. No external sharing, submission or publication is implied.
