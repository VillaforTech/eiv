# Protocol amendment v2 — structural split correction

This amendment preserves the original protocol, dataset, manifest and engineering
results. It is a disclosed design correction **after v1 engineering results were
exposed**, and before any test LLM run. The prior split grouped named scenarios,
but resource-disjunction, insufficient-answer and omission scenarios shared the
same instruction template. Scope-after-clarification also reused the duration
choice template plus a clause unrelated to the requested action. Thus v1 did
**not** satisfy the intended no-cross-split-template requirement; do not present
its nominal family split as independent generalization evidence.

V2 conservatively groups canonical instruction templates. It replaces entity and
condition identifiers and action verbs, removes singleton message recipients to
group analogous file/message patterns, retains disjunction dimensions, negation,
duration and condition structure, and removes unrelated conjuncts for grouping.
Stress interventions and answer sufficiency never define a new independent
template. Every connected template group receives one split, preferring test over
validation over development when merging old split labels. All original cases
and latent labels remain unchanged. Shared simple grammar primitives across
compositional templates are allowed; exact template families cannot cross splits.

The active data are `benchmark/v2/cases.jsonl`: **24 development cases / four
template groups, eight validation / two groups, 40 test / five groups**. The
`family` field now names the independent template group; `scenario_family` retains
the original scenario description, and `original_v1_split` exposes provenance.
Bootstrap resamples these template groups, not the 18 scenario names. With five
test groups, uncertainty remains especially weak and descriptive. The controlled
engineering system and its authors have prior exposure to the designs; v2 is
still not a blinded or independent holdout.

The local LLM development smoke used single-grant prompts, which remain in dev.
No test-model output drove this correction. To keep the pilot feasible on the
installed local model, select **two deterministic cases per test template group**
before running it, preferring one latent allow and one latent deny when both
exist. Save exact IDs and selection hash in a pilot addendum/manifest before
model calls. This yields at most ten cases and is a feasibility pilot, not the
main empirical experiment. Labels remain programmatic and unreviewed. The root
driver records any runtime interruption or missing arm explicitly.

All v1 prompt, information-access, metric and cost constraints continue to apply.
In particular the full-intent oracle removes targeted-question information gain
as a tested variable; the direct-after-disclosure control is exploratory.
Coverage is **exact finite permission-structure match**, not full semantic
equivalence of natural language. Permission list ordering and resource/recipient
ordering are normalized, while logically equivalent but structurally different
policies may be counted as uncovered. Report this proxy limitation.

The human review packet is versioned under `benchmark/v2/human_review/` and has
18 scenario cases with blank review fields. It is not sufficient by itself to
claim independent label validation. The main confirmatory model/human study is
still gated on new reviewed families, a dimension-specific or human answer
oracle, model/budget acceptance, and a separate prospective freeze.
