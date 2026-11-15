# Exact clarification planning: post-hoc engineering extension

This evaluates the current core on already inspected v3 cases and the known greedy-selection counterexample. It is not held-out validation, a human study, or evidence of general LLM safety. Historical manifests and outcomes remain unchanged.

The driver evaluates 1,440 supplied cases across three policies and four budgets, producing 17,280 deterministic outcomes. Only the driver reads latent intent. The core receives public candidates, finite consequences and the answer to its selected question. Repeated cases, orders and budgets are correlated.

## Declared objective

The optional `optimal` policy uses bounded dynamic programming to maximize the count of supplied candidate hypotheses reaching unanimous allow/deny within the budget, then minimize the total questions across all hypotheses (including unresolved branches), then preserve input question order. Each candidate counts once; these are not probabilities of human intent. A branch can stop and abstain when asking cannot improve resolution. Search-limit exhaustion abstains; it never returns an approximate authorization.

## Complete coverage at one question

| Policy | Correct / cases | False allow / latent deny | False deny / latent allow | Abstain / cases | Questions |
|---|---:|---:|---:|---:|---:|
| targeted | 288/288 | 0/144 | 0/144 | 0/288 | 288 |
| first | 96/288 | 0/144 | 0/144 | 192/288 | 288 |
| optimal | 288/288 | 0/144 | 0/144 | 0/288 | 288 |

V3 was constructed with a question that perfectly separates permitting and denying candidates. Matching the targeted policy here is expected; it does not establish general superiority.

## Known eight-candidate counterexample

| Budget | Policy | Correct / 8 | Abstain / 8 | False allow | False deny | Total questions |
|---|---|---:|---:|---:|---:|---:|
| 0 | targeted | 0 | 8 | 0 | 0 | 0 |
| 0 | first | 0 | 8 | 0 | 0 | 0 |
| 0 | optimal | 0 | 8 | 0 | 0 | 0 |
| 1 | targeted | 0 | 8 | 0 | 0 | 8 |
| 1 | first | 1 | 7 | 0 | 0 | 8 |
| 1 | optimal | 1 | 7 | 0 | 0 | 8 |
| 2 | targeted | 1 | 7 | 0 | 0 | 12 |
| 2 | first | 1 | 7 | 0 | 0 | 15 |
| 2 | optimal | 1 | 7 | 0 | 0 | 8 |
| 3 | targeted | 1 | 7 | 0 | 0 | 12 |
| 3 | first | 1 | 7 | 0 | 0 | 15 |
| 3 | optimal | 1 | 7 | 0 | 0 | 8 |

At budget one, exact planning resolves the one identifiable denying hypothesis that greedy pair separation misses. At larger budgets it avoids questions on branches that cannot resolve. This is a post-exposure correction of a known failure, not a prospective comparison. All 18 explicit other/unsure reply checks abstain after one answer.

## Coverage failure remains at one question

| Condition | Policy | False allow / latent deny | False deny / latent allow | Correct / cases | Abstain / cases |
|---|---|---:|---:|---:|---:|
| omit_restrictive | targeted | 144/144 | 0/144 | 144/288 | 0/288 |
| omit_restrictive | first | 144/144 | 0/144 | 144/288 | 0/288 |
| omit_restrictive | optimal | 144/144 | 0/144 | 144/288 | 0/288 |
| omit_permissive | targeted | 0/144 | 144/144 | 144/288 | 0/288 |
| omit_permissive | first | 0/144 | 144/144 | 144/288 | 0/288 |
| omit_permissive | optimal | 0/144 | 144/144 | 144/288 | 0/288 |
| missing_latent_other | targeted | 0/144 | 0/144 | 0/288 | 288/288 |
| missing_latent_other | first | 0/144 | 0/144 | 0/288 | 288/288 |
| missing_latent_other | optimal | 0/144 | 0/144 | 0/288 | 288/288 |
| unsure | targeted | 0/144 | 0/144 | 0/288 | 288/288 |
| unsure | first | 0/144 | 0/144 | 0/288 | 288/288 |
| unsure | optimal | 0/144 | 0/144 | 0/288 | 288/288 |

Removing all restrictive interpretations creates permissive consensus before a question can be asked. The exact planner cannot recover missing hypotheses and preserves this failure. Equal candidate weighting is sensitive to candidate representation and is not a semantic prior. All labels remain programmatic and unreviewed by humans.

## Reproduce

```sh
python3 -m eiv_experiment.planner --output build/planner-check
```

Use a new output directory. Raw outcomes are stored as `raw.jsonl.gz` with a zero timestamp and no embedded filename; the manifest records compressed and uncompressed SHA-256 hashes. Summaries and this analysis are deterministic. Input and current source hashes are checked against changes during execution. The original dataset checksum is verified; original source hashes are intentionally not substituted for this current-core extension. No model is invoked and no external action executes.
