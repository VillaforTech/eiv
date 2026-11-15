# v3 dimension-only clarification: exposed engineering result

AI-authored and inspected finite scenarios; labels are programmatic and unreviewed. No LLM, human participant, real permission enforcement or blind confirmatory evaluation was run.

1,440 constructed cases, 28,800 outcome records, six question orders and question budgets 0/1/2/3. An oracle returns only the chosen dimension answer ID. Repeated orders and budgets are correlated, not extra independent evidence.

## Complete coverage, one-question budget

| Arm | Correct resolved / all | False allow / latent deny | False deny / latent allow | Abstain / all | Questions |
|---|---:|---:|---:|---:|---:|
| direct | 0/288 | 0/144 | 0/144 | 288/288 | 0 |
| ordinary_first | 96/288 | 0/144 | 0/144 | 192/288 | 288 |
| fixed_order | 96/288 | 0/144 | 0/144 | 192/288 | 288 |
| eiv_targeted | 288/288 | 0/144 | 0/144 | 0/288 | 288 |
| abstain_all | 0/288 | 0/144 | 0/144 | 288/288 | 0 |

The targeted policy selects the authorization dimension. Fixed-order policies reach that dimension first in one third of the counterbalanced orders; this is constructed structure, not measured natural-language behavior. With three questions, both first policies resolve every complete-coverage case. There is no measured difference between ordinary_first and fixed_order here: each nuisance partition still separates some unlike-decision pairs.

## Coverage and answer failures, one-question budget

| Condition | Arm | False allow / latent deny | False deny / latent allow | Correct resolved / all | Abstain / all | Questions |
|---|---|---:|---:|---:|---:|---:|
| omit_restrictive | ordinary_first | 144/144 | 0/144 | 144/288 | 0/288 | 0 |
| omit_restrictive | eiv_targeted | 144/144 | 0/144 | 144/288 | 0/288 | 0 |
| omit_permissive | ordinary_first | 0/144 | 144/144 | 144/288 | 0/288 | 0 |
| omit_permissive | eiv_targeted | 0/144 | 144/144 | 144/288 | 0/288 | 0 |
| unsure | ordinary_first | 0/144 | 0/144 | 0/288 | 288/288 | 288 |
| unsure | eiv_targeted | 0/144 | 0/144 | 0/288 | 288/288 | 288 |
| missing_latent_other | ordinary_first | 0/144 | 0/144 | 0/288 | 288/288 | 288 |
| missing_latent_other | eiv_targeted | 0/144 | 0/144 | 0/288 | 288/288 | 288 |

Omitting every restrictive reading leaves an unsafe permissive consensus; omitting every permissive reading yields false denial. The oracle is never called after consensus. An explicit other/unsure answer terminates with abstention when a question is actually asked. Therefore targeted selection does not solve interpretation coverage.

## Reproduction and interpretation

The manifest freezes dataset bytes, this module, the protocol and the finite core before execution. Raw rows retain candidate IDs, formal statuses, selected-question scores, oracle answer IDs, restriction traces and outcome flags. Summary denominators are exact and stratified by budget, condition, family and question position. There are no bootstrap confidence bands: this exhausts a tiny author-constructed space and is not a random sample. Local electricity, hardware and development time are unpriced.

Run `python3 -m eiv_experiment.dimensions --verify-only` to verify the freeze; use a fresh `--output` directory to reproduce all 28,800 outcomes without inference or external services.
