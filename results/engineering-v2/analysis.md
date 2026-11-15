# Controlled engineering results

These are deterministic controlled-language policies, not an empirical LLM superiority result. Labels are synthetic and unreviewed; uncertainty is descriptive across template families.

| Arm | False allow / latent deny | False deny / latent allow | Correct resolved / all | Abstain / all | Questions | Initial intent coverage / all |
|---|---:|---:|---:|---:|---:|---:|
| conventional | 0/25 | 0/15 | 28/40 | 12/40 | 40 | 32/40 |
| direct | 4/25 | 4/15 | 7/40 | 25/40 | 0 | 32/40 |
| eiv | 4/25 | 4/15 | 28/40 | 4/40 | 25 | 32/40 |
| eiv_first_candidate | 12/25 | 9/15 | 19/40 | 0/40 | 0 | 18/40 |
| eiv_first_question | 4/25 | 4/15 | 28/40 | 4/40 | 25 | 32/40 |
| eiv_no_exhaustive_verifier | 4/25 | 4/15 | 28/40 | 4/40 | 25 | 32/40 |

Missing-intent perturbations are deliberately induced stressors, not population prevalence. Candidate agreement still permits false authorization. Abstention is counted as unresolved, never as a correct answer.

## Paired comparisons and examples

### EIV versus conventional

Families: 5. Differences are EIV minus comparator. Correct-resolved difference 0.000; descriptive family-bootstrap interval [0.0, 0.0].

- helps: none observed
- no_change: conditional_duration_choice-01, conditional_duration_choice-02, conditional_duration_choice-03
- harms: none observed
- false_authorization_harms: omitted_restrictive_reading-01, omitted_restrictive_reading-02, omitted_restrictive_reading-03

### EIV versus direct

Families: 5. Differences are EIV minus comparator. Correct-resolved difference 0.525; descriptive family-bootstrap interval [0.2647058823529412, 0.9375].

- helps: conditional_duration_choice-02, conditional_duration_choice-03, conditional_duration_choice-04
- no_change: conditional_duration_choice-01, conditional_resource_choice-02, insufficient_answer-01
- harms: none observed
- false_authorization_harms: none observed

### EIV versus eiv_first_candidate

Families: 5. Differences are EIV minus comparator. Correct-resolved difference 0.225; descriptive family-bootstrap interval [0.04411764705882354, 0.5].

- helps: conditional_duration_choice-02, conditional_resource_choice-03, conditional_resource_choice-04
- no_change: conditional_duration_choice-01, conditional_duration_choice-03, conditional_duration_choice-04
- harms: insufficient_answer-01, insufficient_answer-02
- false_authorization_harms: none observed

### EIV versus eiv_first_question

Families: 5. Differences are EIV minus comparator. Correct-resolved difference 0.000; descriptive family-bootstrap interval [0.0, 0.0].

- helps: none observed
- no_change: conditional_duration_choice-01, conditional_duration_choice-02, conditional_duration_choice-03
- harms: none observed
- false_authorization_harms: none observed

### EIV versus eiv_no_exhaustive_verifier

Families: 5. Differences are EIV minus comparator. Correct-resolved difference 0.000; descriptive family-bootstrap interval [0.0, 0.0].

- helps: none observed
- no_change: conditional_duration_choice-01, conditional_duration_choice-02, conditional_duration_choice-03
- harms: none observed
- false_authorization_harms: none observed

## Limits

The first-question ablation may be identical because this grammar exposes only one full-interpretation question. The direct-Boolean ablation preserves permission semantics and is expected to match exhaustive checking. Neither null contrast establishes that verification or targeted question selection is useless in richer systems. Latency is local and machine-dependent; local energy/hardware costs are not priced. Raw JSONL preserves every generated case, decision and trace; summary.json contains denominators, cost, per-family results and descriptive uncertainty.
