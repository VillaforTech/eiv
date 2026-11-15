# EIV v0.4.0 — Formal permission models and inspectable decisions

EIV is an open-source research-engineering project by Roberto Villafuerte. It makes a proposed agent operation inspectable: represent possible permission meanings, check each against a finite action model, clarify when useful, and preserve the evidence behind the decision.

This release provides the decision and trace layer for **simulated** file and message permissions. It includes a Python CLI, a local interactive workbench, reproducible experiments, an academic report, and a portfolio website draft.

### What's included

- **Explicit permission semantics:** candidate policies distinguish action, resource, recipient, scope, conditions, and prohibitions. Decisions expose their checks, assumptions, and finite-model results.
- **Bounded clarification:** compare first-question and greedy strategies with an optional exact planner. The planner maximizes the number of supplied hypotheses resolved within a question budget, then minimizes total questions. Stopping and abstaining is an explicit option.
- **Inspectable traces:** review represented meanings, clarification answers, candidate filtering, and final allow/deny/abstain decisions. Traces record observable evidence, not hidden chain-of-thought or proof of actual human intent.
- **Robust local tooling:** strict JSON and session validation, computation and HTTP resource bounds, packaged workbench assets, and adversarial regression tests. Runtime and replay require no third-party dependencies or model calls.
- **Preserved research evidence:** historical experiments replay with archived source, while the current planner comparison remains separately versioned. Earlier failures and negative results remain visible.
- **Open-source foundations:** MIT license, citation metadata, verified academic bibliography, contributor and security guidance, issue/PR templates, and a versioned CI workflow.

### What the evidence establishes

The exact planner addresses a known greedy-selection counterexample: with one question, it resolves 1/8 possible intents where the greedy rule resolves 0/8. This is a **post-hoc engineering correction**, not a held-out performance claim.

The central limitation remains: a correct verifier can approve the wrong operation when the intended policy is absent. In the deliberately constructed restrictive-omission condition, all three evaluated strategies falsely allow all 144 latent-deny cases. The benchmarks are synthetic, correlated, and unreviewed by independent humans; their counts do not estimate real-world safety.

### Try it

```sh
git clone https://github.com/VillaforTech/eiv.git
cd eiv
python3 scripts/restore_evidence.py
python3 -m eiv.web
```

Open `http://127.0.0.1:8765`. Try recipient ambiguity, inspect the trace, and compare strategies on the selector counterexample. Python 3.10+ is required.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/reproduce.py --output build/reproduction-unique
python3 -m eiv_experiment.planner --output build/planner-comparison
```

The Git checkout stores large historical evidence as compressed parts; restoration
verifies their original bytes locally, without network calls. The attached source
ZIP already includes the restored data. Use fresh output directories. This release does not execute real actions, integrate a live conversational agent, or issue authenticated permission tokens. Those extensions have separate design and validation requirements.

Read the [formal action model](https://github.com/VillaforTech/eiv/blob/v0.4.0/docs/formal-action-model.md), [research report](https://github.com/VillaforTech/eiv/blob/v0.4.0/docs/research-report.md), [planner results](https://github.com/VillaforTech/eiv/blob/v0.4.0/results/planner-v4/analysis.md), and [contribution guide](https://github.com/VillaforTech/eiv/blob/v0.4.0/CONTRIBUTING.md). The [portfolio draft](https://github.com/VillaforTech/eiv/blob/v0.4.0/portfolio/index.html) is source for a future website presentation.
