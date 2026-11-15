# Local LLM feasibility pilot

Same installed Gemma 2 9B Q4_0 model, synthetic unreviewed labels, five template groups. This is an exploratory feasibility pilot, not the confirmatory experiment. Full-intent disclosure after any question prevents a claim about targeted question quality. Direct-after-disclosure receives free additional information and is a separate exploratory control.

| Method | False allow / deny cases | False deny / allow cases | Correct / all | Abstain | Questions | Calls | Output tokens | Median seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| conventional | 3/5 | 1/5 | 6/10 | 0 | 2 | 22 | 1021 | 13.8 |
| direct | 2/5 | 1/5 | 6/10 | 1 | 0 | 20 | 1091 | 15.2 |
| eiv | 1/5 | 2/5 | 7/10 | 0 | 0 | 10 | 763 | 12.1 |

Schema failures and backend errors remain in the denominator and raw traces. External API spend is $0; local energy, hardware and user time are not valued. Re-running generation is not guaranteed bit-for-bit across runtime/hardware; replaying these raw outputs reproduces the reported analysis.

## Paired descriptive uncertainty

- EIV minus conventional: correct-resolution difference 0.100; family-bootstrap 95% percentile interval [0.0, 0.30000000000000004]. Only 5 template groups; no generalization or significance claim.
  Helps: ['recipient_exception-02', 'conditional_duration_choice-01', 'duration_disjunction-03']; ties: ['insufficient_answer-01', 'conditional_resource_choice-02', 'insufficient_answer-03']; harms: ['duration_disjunction-01', 'conditional_duration_choice-02'].
- EIV minus direct: correct-resolution difference 0.100; family-bootstrap 95% percentile interval [0.0, 0.30000000000000004]. Only 5 template groups; no generalization or significance claim.
  Helps: ['recipient_exception-02', 'conditional_duration_choice-01', 'duration_disjunction-03']; ties: ['insufficient_answer-01', 'conditional_resource_choice-02', 'insufficient_answer-03']; harms: ['duration_disjunction-01', 'conditional_duration_choice-02'].

EIV exact-structure intention coverage: initially 6/10; final all-case rate 0.6. Logical equivalence can be missed by this proxy; a human semantic audit is still required.

Error counts: `{"conventional": {"invalid_model_schema": 1}, "direct": {}, "eiv": {}}`.

Raw data are the source of each result. Human label review, a question-specific oracle, independent families and a stronger-model replication are still required before testing the general research claim.
