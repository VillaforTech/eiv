# Synthetic permission benchmark — active version 2

**Use `v2/cases.jsonl` and `v2/manifest.json`.** V1 remains preserved below for
provenance. Independent review found that named v1 scenario families reused
instruction templates across splits. V2 corrects grouping by canonical instruction
structure, preserves every label, and discloses earlier engineering exposure in
`research/protocol-v2-amendment.md`. It is not a blinded holdout. V2 has 24 dev / 8
validation / 40 test cases, clustered into 4 / 2 / 5 actual template groups.
Review `v2/human_review/packet.md` and fill its blank `review.csv`.

## Original version 1 (retained, superseded split)

72 hand-designed template instantiations across files and messages; 18 families,
four cases per family. **All labels are programmatic and unreviewed.** No real
people, private messages, production resources, or imported corpus are included.
The numeric resource suffixes are synthetic identifiers, not language variety.
English controlled instructions are a deliberate engineering boundary.

Original split: 32 development, 16 validation, 24 test. Named scenario families
remained in one split, but shared templates crossed splits; v2 corrects this. This is not
an independently collected natural-language test. Freeze occurred before runs,
but implementation authors know the design; it is not blinded. Test artifact
hashes and prompt/protocol hashes are in `manifest.json`.

Fields: `instruction/request/facts` are public initial inputs. `latent_intent`
contains a synthetic intended interpretation and structured permissions.
`latent_facts` fixes actual condition truth, which may be partly hidden from the
system. `expected_decision` is the intended allowed/forbidden classification;
`permitted_actions/forbidden_actions` cover the **single requested atom**, not all
possible actions in the world. `oracle_answers` maps the controlled parser's
question `interpretation` to a candidate id or `unsure`; dynamic model queries use
the full-intent oracle documented in the protocol. `generator_perturbation`
specifies a stress intervention in engineering runs only. No model sees it.

Missing-intent interventions drop all generated readings with one requested
decision; they intentionally create unrepresentative worst cases. Do not use
their frequency as a prevalence estimate. Labels must not leak into initial
prompts. One intended reading may be absent while another has the same decision;
coverage and decision correctness are separate quantities.

`generate.py` deterministically enumerates v1, refuses to overwrite an existing
file, and uses no randomness for labels. Seed 20261012 is fixed for resampling.
`python -m eiv_experiment.run --verify-only` checks active v2; add
`--benchmark-version 1` to verify preserved v1. Neither command runs a model.
Any content correction after freeze must preserve v1 and receive a new
version or explicit deviation record; do not silently regenerate it.

Human review: open `human_review/packet.md`, fill `human_review/review.csv`, and
record disagreements even if the implementation already agrees with a label.
The packet contains one case per family (18); all approval fields are blank.
The user may choose to change a latent policy if the prompt does not plausibly
support it; that produces a new benchmark version, not a retroactive score fix.

Conditions of use: private project evaluation only pending the owner's explicit
publication/license decision. No public dataset license is asserted. Attribution
for the generated material is this project and its recorded generator; there are
no third-party examples. Report the version/hash, unreviewed status, split method,
controlled grammar, omission interventions, and optimistic oracle in any result.
