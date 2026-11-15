# EIV: verified consequences, unverified intent

**Interactive Verifiable Specification · Roberto Villafuerte · 14 November 2026**  
Independent research software and reproducible engineering study. Evidence from the preserved October 2026 experiments; bibliography rechecked on 14 November 2026.

## Abstract

An agent can verify a permission correctly and still authorize the wrong action if its interpretation of the user's intent is incomplete. EIV makes this boundary inspectable. It represents a small set of possible permission policies, evaluates a fixed symbolic request under each policy, asks a bounded clarification when consequences disagree, and otherwise returns a simulated allow, deny, or abstain decision. The contribution is an executable investigation of candidate coverage, clarification selection, and the limits of formal checking—not a general solution to agent authorization. In a preserved 40-case controlled-language study, EIV and its conventional comparator both resolve 28 cases correctly; EIV asks fewer questions but introduces eight incorrect decisions. A subsequent constructed study separates question selection from semantic generation: with complete coverage and one question, targeted selection resolves 288/288 cases versus 96/288 for an ordinary-first selector. Removing all restrictive interpretations nevertheless causes 144/144 false authorizations on latent-deny cases. A separate counterexample disproves general budget-optimality of the selection heuristic. These finite, AI-authored, human-unreviewed experiments establish reproducible mechanism behavior, not real-world safety or general LLM superiority.

## 1. Problem and contribution

Consider the instruction “You may send report to alex or bea once” and the request to send it to Alex. Possible policies grant Alex, Bea, or both recipients. Those interpretations have different authorization consequences. A conventional Boolean permission check can answer whether a supplied policy permits the request; it cannot establish that the supplied policy is what the person meant.

EIV studies two questions:

1. Can disagreement about a request's consequences guide which clarification to ask within a small interaction budget?
2. What breaks when the intended permission is absent from the candidate set, even if every represented policy is checked correctly?

The artifact provides a bounded permission language, a finite evaluator, a deterministic clarification loop, a local interactive workbench, a command-line interface, frozen experiments, replayable model output, and separately implemented result checks. Its engineering advantages are transparent decisions, explicit abstention, inspectable traces, and reproduction without model inference. These are implemented properties; reductions in real-world harm or human effort remain hypotheses.

The research contribution is the **joint characterization of clarification benefit and semantic-coverage failure in a small reproducible authorization setting**, including negative results and a counterexample to the chosen heuristic. No claim of priority, state-of-the-art performance, or a peer-reviewed research result is made.

## 2. Relation to prior work

Interactive interpretation is established research. Yao et al. [1] describe semantic-parsing agents that maintain a parse, decide when intervention is needed, ask a question, and update their state. CLAM [2] studies selective clarification with generative language models and simulated users. EIV adapts this interaction pattern to permission consequences; it does not introduce the pattern.

Formalization also has an interactive history. **nl2spec** [3] maps natural-language fragments to temporal-logic subformulas and lets users revise those mappings. EIV instead exposes bounded permission choices and evaluates a fixed action. Neither the use of formal representations nor human correction of a translation is novel here.

AMBROSIA [4] constructs text-to-SQL examples where ambiguity survives the available database context. Saparina and Lapata [5] subsequently address missing interpretations using disambiguation before parsing and an infilling model. These works motivate distinguishing the existence of multiple candidates from coverage of the intended reading. EIV's exact finite-policy match is a narrower coverage proxy than human semantic equivalence; EIV does not implement an infilling model.

Recent adjacent work further limits the novelty claim. FAVA [6] describes LLM-guided permission representations, deterministic graph construction, SMT authorization, and runtime enforcement. BAL [7] selects clarification questions over grounded temporal specifications and connects the result to robot planning. EIV neither reproduces their evaluations nor provides their execution machinery. Its specific role is a small, auditable testbed for asking what consensus and question selection can establish when intent coverage is uncertain. Comparisons in this paragraph concern mechanisms, not numerical performance across incompatible tasks.

This is a focused primary-source review, not a systematic literature survey. The bibliography contains verified publication or author-hosted records; no third-party dataset or source code was imported to produce the EIV benchmark.

## 3. System and mathematical contract

### Representation and decisions

A request fixes five fields: domain, action, resource, recipient, and scope. The file domain supports symbolic read/write/delete operations; messages support symbolic send. Scope is once or session. Conditions refer to named Boolean facts; an omitted fact is unknown. Candidates contain explicit allow/deny permissions. Questions partition candidate IDs into answer groups. A normal answer can only retain existing candidates; it cannot create a permission, change facts, or broaden the request.

Each candidate is checked against the same request and fact map. Permission matching produces the predicates `Granted` and `Prohibited`; the formal authorization condition is:

\[
\mathrm{Authorized}\leftrightarrow(\mathrm{Granted}\land\neg\mathrm{Prohibited}).
\]

A consistency condition excludes simultaneous applicable grants and prohibitions. Unknown relevant conditions, contradictory permissions, unsupported semantic input, and exhausted checking bounds do not become an allow decision. The permission layer returns abstention for these unresolved situations. The general finite evaluator distinguishes entailed, refuted, underdetermined, inconsistent, and resource-limited results; its checks are relative to the supplied finite theory.

At the interaction layer, unanimous allow or deny among active candidates terminates. Otherwise, an available question may be asked. Exhausted budgets or unresolved disagreement produce abstention. The nonselecting responses `other` and `unsure` also terminate with abstention when a question is actually presented. This last qualification matters: no rejection opportunity is offered after an already-unanimous but incomplete candidate set.

### Conditional consensus proposition

Let \(C_0\ne\varnothing\) be the initial candidate set, \(p^*\) the intended policy, \(r\) a fixed request, and \(F\) the fact map. Assume:

- \(p^*\in C_0\), and that candidate faithfully represents the intended permission;
- the language captures every relevant identity, effect, and condition, and \(F\) is correct;
- candidate evaluation is correct within the declared finite semantics and bounds;
- each clarification retains \(p^*\);
- instruction, request, and facts remain fixed during the session.

Then a unanimous terminal allow implies that \(p^*\) permits \(r\) in the declared semantics; unanimous deny implies that it does not.

**Argument.** Membership of \(p^*\) in the active set is invariant: it holds initially and each answer preserves it. At unanimity, its evaluated decision therefore equals the emitted decision. Correct evaluation and faithful representation connect that decision to the intended finite policy. This is a short mathematical argument, not a mechanized verification of the implementation. It does not establish any assumption from unrestricted prose.

If coverage fails, the conclusion need not hold. For example, candidates granting Alex alone and both Alex and Bea agree to allow a send to Alex. A missing intended policy granting only Bea makes that consensus wrong. More exhaustive checking of the represented candidates cannot reveal the missing policy.

### Question selection

The targeted heuristic scores a question by counting active candidate pairs with different decisions that fall in different answer groups. It chooses the highest score, breaking ties by declaration order. This uses public candidate consequences, not latent intent. It is not a calibrated information-gain estimate, a probability distribution over users, or a general optimality criterion. The preserved counterexample in Section 4 demonstrates the distinction.

## 4. Evidence and results

### Controlled-language study: a negative tradeoff

The corrected v2 dataset contains 24 development, eight validation, and 40 test cases, grouped by canonical instruction templates. The test set has only five template groups. Earlier exposure to the authored designs means this is not a blinded holdout. Its full-intent answer oracle cannot isolate targeted question quality.

| v2 method | Correct / all | False allow / latent deny | False deny / latent allow | Abstain / all | Questions |
|---|---:|---:|---:|---:|---:|
| Conventional clarification | 28/40 | 0/25 | 0/15 | 12/40 | 40 |
| EIV | 28/40 | 4/25 | 4/15 | 4/40 | 25 |
| Direct consensus | 7/40 | 4/25 | 4/15 | 25/40 | 0 |

EIV reduces the question count by 15 while preserving the count of correct resolutions, but replaces eight abstentions with four false authorizations and four false denials. That is not an unqualified improvement. The first-question ablation and direct-Boolean verification ablation match EIV here. The grammar often supplies one useful full-interpretation question; direct Boolean checking preserves the same permission semantics. These null comparisons neither establish a selection advantage nor show that formal checking is unnecessary in richer systems.

Evidence: [analysis](../results/engineering-v2/analysis.md), [summary](../results/engineering-v2/summary.json), and [raw outcome distribution](../evidence/distribution/README.md).

### Saved local-model feasibility pilot

A preserved Gemma 2 9B Q4_0 pilot evaluates ten cases across five template groups. EIV resolves 7/10 correctly, with 1/5 false authorizations and 2/5 false denials. Conventional and direct methods each resolve 6/10. EIV generates one candidate per case and asks zero questions, so this pilot does **not** test targeted clarification. Exact-structure intent coverage is 6/10. Full-intent disclosure in querying arms, small sample size, synthetic labels, and representation differences prevent a general superiority claim. Reanalysis of the saved outputs is deterministic; new generation is a different experiment and may not reproduce identical text.

Evidence: [pilot analysis](../results/llm-pilot-v2-analysis/analysis.md) and [saved outputs](../results/llm-pilot-v2.jsonl). This report adds no new model inference.

### Dimension-only study: selection can help in a constructed space

V3 supplies candidates directly and isolates the selection mechanism. Six symbolic scenarios share one three-bit decision structure: one binary dimension controls the requested operation, while two change unrelated permissions. Each scenario has eight latent policies and six question orders. Five conditions produce \(6\times8\times6\times5=1{,}440\) cases. Five policies at four budgets yield 28,800 outcome records. An oracle reveals only the dimension actually asked; it does not disclose the whole intended policy.

| Complete coverage, budget 1 | Correct / all | Abstain / all | Questions |
|---|---:|---:|---:|
| Direct consensus | 0/288 | 288/288 | 0 |
| Ordinary-first | 96/288 | 192/288 | 288 |
| Fixed order | 96/288 | 192/288 | 288 |
| EIV targeted | 288/288 | 0/288 | 288 |
| Always abstain | 0/288 | 288/288 | 0 |

Every method in this table has zero false allows among 144 latent-deny cases and zero false denials among 144 latent-allow cases. The targeted question perfectly separates consequences **by construction**. At budget three, ordinary-first and targeted both resolve 288/288, using 576 and 288 questions respectively. This shows the mechanism operating on its designed structure; it is not a measurement of typical user instructions or LLM behavior.

Coverage interventions expose the main failure. Removing every restrictive candidate yields 144/144 false authorizations on latent-deny cases for both ordinary-first and targeted. Removing every permissive candidate yields 144/144 false denials on latent-allow cases. Both stop at consensus with zero questions. Under `unsure`, and when a missing latent candidate is explicitly rejected with `other`, both abstain on all 288 cases after asking. These latter results test responses to an available rejection signal; they do not demonstrate automatic detection of missing intent.

Evidence: [v3 analysis](../results/dimensions-v3/analysis.md), [summary](../results/dimensions-v3/summary.json), [raw outcome distribution](../evidence/distribution/README.md), and [protocol](../research/protocol-v3.md).

### Counterexample: pair separation is not budget optimality

A separate post-exposure audit uses eight fully represented policies: four allow and four deny. Question `balanced` has pair score eight but leaves both answer groups mixed. Question `isolate` scores four but has one pure denying singleton group. At a one-question budget, targeted selection resolves **0/8** possible intents; the first-question comparator selects `isolate` and resolves **1/8**. Neither makes an incorrect resolved decision. At budget two both resolve 1/8, using 12 versus 15 total questions. Equal candidate counting here is exhaustive accounting, not a human-intent prior.

The same audit separately recomputes 240 v2 and 28,800 v3 records and their metrics. Agreement between implementations strengthens internal correctness; it does not provide independent human labels or statistical replication. Evidence: [audit and counterexample](../results/selection-audit-final-20261023/analysis.md).

### v0.4 extension: exact planning for a declared finite objective

The optional `optimal` strategy in [planning.py](../eiv/planning.py) addresses the known selection defect with bounded dynamic programming. Its objective is lexicographic: maximize the number of supplied candidate hypotheses that reach a unanimous allow/deny leaf within the remaining budget; then minimize the sum of questions along **all** candidate paths, including unresolved paths; finally prefer input question order. Every candidate has weight one. These are finite counts, not learned probabilities of human intent, and duplicating equivalent interpretations can change the objective's weighting.

Stopping with abstention is an explicit option, so the planner does not ask a question with no eventual resolution benefit. It assumes truthful selecting answers, fixed candidate consequences, and the declared partitions. It searches at most 20,000 states and 200,000 question transitions by default; exhausting a bound causes abstention through the permission layer, without returning a partially searched plan as exact. `other` and `unsure` continue to abstain. The CLI and workbench expose this strategy separately; the historical greedy strategy remains the default.

On the **already-known** eight-policy counterexample, the extension resolves 1/8 possibilities with one question versus greedy's 0/8. At budget two, both resolve 1/8, but exact planning uses eight total questions versus greedy's twelve. These counts were checked by enumerating all eight truthful paths through the current API/session integration. Eleven planner tests pass, including 564 comparisons against an uncached, set-based recursive reference over legal question choices, multi-answer partitions, abstaining candidates, tie handling, and resource-limit failures. A CLI check selects `isolate` at budget one.

This is a post-exposure engineering correction under an explicit finite objective, **not** prospective evidence of better human interaction. It does not add omitted interpretations, verify intent coverage, or repair false consensus. Historical v2/v3 results above remain unchanged; the extension is not retroactively substituted into those experiments.

## 5. Validity, reproducibility, and appropriate use

All benchmark cases and labels are AI-authored, inspected, and unreviewed by independent humans. V3 orders, budgets, and scenario variants are strongly correlated; 28,800 rows do not mean 28,800 independent observations. The stressor frequencies are chosen by design and estimate no population prevalence. No confidence interval can turn exhaustive enumeration of this tiny designed space into evidence about unrestricted deployment.

The implemented grammar is deliberately narrow. Structured validity does not establish semantic fidelity. Facts are assumed trusted; identity, effect modeling, and user answers can be wrong. A local simulated allow is not an execution credential. The system does not enforce real tools, authenticate users, track revocation, model concurrent effects, or establish resistance to indirect prompt injection. Its research value is to expose these boundaries clearly enough to test them.

From a source checkout, the unit suite and reproducibility entry point are:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/reproduce.py --output build/research-replay
```

Use a fresh output directory. The reproduction script tests current software and replays historical experiments with isolated archived source; it does not silently rewrite original source manifests to accommodate live changes. Replay requires no network inference. Hashes verify artifact identity, not truthful semantics. Unit tests and separate replay calculations are engineering evidence, not a proof that every implementation behavior satisfies the mathematical contract.

The next empirical study requires independently authored and human-reviewed permission families, a prospective split and freeze, a realistic answer channel, comparable information and compute budgets, and model baselines that can both ask and abstain. The exact planner's declared objective should be evaluated prospectively against these baselines and alternative cost assumptions. Neither that study nor production integration is represented as completed work.

## References

Machine-readable citations: [references.bib](../research/references.bib).

1. Ziyu Yao, Yu Su, Huan Sun, and Wen-tau Yih. 2019. *Model-based Interactive Semantic Parsing: A Unified Framework and A Text-to-SQL Case Study*. EMNLP-IJCNLP, 5447–5458. [ACL Anthology](https://aclanthology.org/D19-1547/). DOI: 10.18653/v1/D19-1547.
2. Lorenz Kuhn, Yarin Gal, and Sebastian Farquhar. 2022; revised 2023. *CLAM: Selective Clarification for Ambiguous Questions with Generative Language Models*. arXiv preprint, version 2. [arXiv](https://arxiv.org/abs/2212.07769v2). DOI: 10.48550/arXiv.2212.07769.
3. Matthias Cosler, Christopher Hahn, Daniel Mendoza, Frederik Schmitt, and Caroline Trippel. 2023. *nl2spec: Interactively Translating Unstructured Natural Language to Temporal Logics with Large Language Models*. CAV, 383–396. [Publisher](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18). DOI: 10.1007/978-3-031-37703-7_18.
4. Irina Saparina and Mirella Lapata. 2024. *AMBROSIA: A Benchmark for Parsing Ambiguous Questions into Database Queries*. NeurIPS 37, Datasets and Benchmarks Track. [Proceedings](https://papers.nips.cc/paper_files/paper/2024/hash/a4c942a8405cc910f0a833d28d2573cc-Abstract-Datasets_and_Benchmarks_Track.html). DOI: 10.52202/079017-2876.
5. Irina Saparina and Mirella Lapata. 2025. *Disambiguate First, Parse Later: Generating Interpretations for Ambiguity Resolution in Semantic Parsing*. Findings of ACL, 16825–16839. [ACL Anthology](https://aclanthology.org/2025.findings-acl.863/). DOI: 10.18653/v1/2025.findings-acl.863.
6. Yifan Zhang, Xinkui Zhao, Sai Liu, Hengxuan Lou, Guanjie Cheng, and Chang Liu. 2026. *FAVA: Formal Authorization for Verified Agents with Evidence-Backed Permission Graphs*. arXiv preprint 2607.27267. [arXiv](https://arxiv.org/abs/2607.27267). The comparison above uses the primary abstract; the full text was not accessible during this bibliography recheck.
7. Huao Li, Carson Sobolewski, Augustinos Saravanos, William Tan, John Karigiannis, and Chuchu Fan. 2026. *Bayesian Active Learning for Intent Disambiguation in Interactive Robot Planning*. arXiv preprint 2609.34270. [Authors' project and publication record](https://www.huao-li.com/bal/); [arXiv](https://arxiv.org/abs/2609.34270). The project page reports CoRL 2026; this report does not rely on an independently verified proceedings version.

## Reproduced planner extension

The new [post-hoc comparison](../results/planner-v4/analysis.md) runs the current core on all 1,440 exposed v3 cases under three strategies and budgets 0–3: 17,280 outcomes. A separate 96-path counterexample evaluation and 18 `other`/`unsure` checks exercise the new planner. All seven result artifacts reproduced byte for byte. The exact strategy matches the greedy strategy on the constructed complete-coverage cases, resolves 1/8 rather than 0/8 paths in the known one-question counterexample, and reduces unnecessary questions at larger budgets. It still falsely authorizes 144/144 latent-deny cases when restrictive readings are omitted. This is a tested mechanism extension on exposed data, not a new generalization result.
