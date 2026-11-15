# Inspect a decision trace

`recipient-clarification.json` contains an initial and final replay session
produced by the current Python core. It is a synthetic, non-executing example.

The request proposes sending `report` to `alex`. Three supplied interpretations
permit Alex, Bea, or either recipient. The user selects the Bea-only reading;
the checked decision becomes `deny`. Inspect these fields:

- `case`: instruction, symbolic request, supplied facts and candidate policies.
- `question_strategy`: the chosen bounded planning strategy.
- `answers`: observable user selections.
- `result.candidates`: dimension/condition checks and formal outcomes.
- `result.trace`: generated candidate IDs, filtering events and final decision.

A trace records represented meaning and computation. Candidate coverage remains
unverified. There is no executed message, authenticated approval or hidden model
reasoning in this file. See the [formal action model](../../docs/formal-action-model.md).
