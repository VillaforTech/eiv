# Post-v3 independent evidence and selection audit

This is a post-exposure, AI-assisted engineering audit. No frozen v2/v3 inputs, source or results were changed. It supplies no independent human labels, statistical replication or model inference.

The separate denotation/aggregation code checked all 240 v2 records and 28,800 v3 records, with exact case/arm/budget completeness. Every saved v3 trace and answer sequence matches a separately implemented finite-set replay. Outcome flags and aggregate/stratified metrics agree. V2 paired descriptive family-bootstrap intervals were independently recomputed and match; their original weak inferential scope does not change.

## Counterexample: pair separation is not one-question resolution

Eight distinct, fully represented finite policies have four allowing and four denying consequences. Two legal binary questions share the same input and answer channel. `balanced` splits each decision class evenly: score 8, with both answer groups still mixed. `isolate` separates one denying policy from the other seven: score 4, with one pure denying branch. Both use a binary answer channel. The isolate question's singleton response identifies one of eight policies; binary channel size does not imply equal information in every response.

A one-step resolution comparator counts public candidate IDs in answer groups whose finite decisions already agree. It assigns balanced 0/8 and isolate 1/8, selecting isolate without consulting the latent policy or gold label. It coincides with the real core's evaluated first-question comparator here. This equal candidate accounting is not a probability model of human intention, and the comparator is not claimed optimal beyond this one-step objective.

The real EIV core strictly prefers score 8 over score 4. Its existing first-positive-score comparator chooses the declared isolate question first. All eight possible intended policies and every resulting truthful answer path are enumerated at budgets zero, one and two. This is a counterexample to budget-optimality, not a claim about the prevalence or human usability of these questions.

| Budget | Targeted correct / 8 | First correct / 8 | Targeted abstain / 8 | First abstain / 8 | Targeted questions | First questions |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 8 | 8 | 0 | 0 |
| 1 | 0 | 1 | 8 | 7 | 8 | 8 |
| 2 | 1 | 1 | 7 | 7 | 12 | 15 |

Neither method makes an incorrect resolved decision: coverage is complete and replies are truthful. At one question, first resolves 1/8 possibilities versus targeted 0/8. At two questions they tie on 1/8 resolution, with targeted using fewer questions. An explicit other or unsure answer abstains in all eight strategy/budget/reply checks. The equal candidate counts above are exhaustive finite accounting, not a calibrated or inferred probability distribution over people.

## Consequence for the scientific claim

V3 intentionally includes a question that perfectly separates all opposite-decision pairs, so the greedy score selects that question. Its positive result does not establish that the score generally optimizes resolution under a budget. This new example uses the unmodified core and retains the null/negative behavior. A future policy could optimize a declared expected-resolution or worst-case objective, but would need an explicit distribution or robustness criterion and a new prospective evaluation. No replacement policy is tuned into v3.

## Reproduce

`python3 -m eiv_experiment.selection_audit --output build/new-selection-audit`

Use a fresh output directory. The manifest identifies audited evidence hashes, audit source and the unchanged core. Saved JSON contains the legal input, all 48 truthful candidate/strategy/budget records, eight nonselecting-reply checks and exact denominators. This check never calls a model, a network inference service or an actual file/message action.
