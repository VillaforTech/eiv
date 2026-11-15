"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
require("./demo.js");
const E = globalThis.EIVDemo;

test("every strategy, budget, and coverage setting has the declared behavior", () => {
  for (const strategy of ["targeted", "first"]) {
    for (let budget = 0; budget <= 3; budget++) {
      for (const omission of [false, true]) {
        let state = E.create({ strategy, budget, omission });
        while (E.analyze(state).decision === "ask") state = E.step(state);
        const resolves = (strategy === "targeted" && budget >= 1) || (strategy === "first" && budget >= 3);
        assert.equal(E.analyze(state).decision, omission ? "allow" : resolves ? "deny" : "abstain");
        assert.equal(state.answers.length, omission ? 0 : Math.min(budget, strategy === "targeted" ? 1 : 3));
      }
    }
  }
});

test("pair score selects recipient without access to the latent intent", () => {
  const targeted = E.analyze(E.create());
  assert.equal(targeted.question.id, "recipient");
  assert.equal(targeted.score, 16);
  const first = E.analyze(E.create({ strategy: "first" }));
  assert.equal(first.question.id, "format");
  assert.equal(first.score, 8);
  // Changing public labels without altering candidate decisions leaves selection unchanged.
  const state = E.create();
  for (const candidate of state.candidates) {
    candidate.recipient = candidate.recipient === "Alex" ? "unknown-A" : "unknown-B";
  }
  assert.equal(E.analyze(state).question.id, "recipient");
  assert.equal(E.analyze(state).score, 16);
});

test("other and unsure abstain; stepping leaves prior state unchanged", () => {
  const state = E.create();
  const original = JSON.stringify(state);
  for (const answer of ["other", "unsure"]) {
    const next = E.step(state, answer);
    assert.equal(E.analyze(next).decision, "abstain");
    assert.equal(next.answers.length, 1);
  }
  const next = E.step(state);
  assert.deepEqual(next.active, ["c5", "c6", "c7", "c8"]);
  assert.equal(JSON.stringify(state), original);
});

test("invalid configurations and answers do not invent a decision", () => {
  for (const config of [{ budget: -1 }, { budget: 4 }, { budget: 1.5 }, { strategy: "best" }, { omission: "yes" }]) {
    assert.throws(() => E.create(config), TypeError);
  }
  assert.throws(() => E.step(E.create(), "allow"), TypeError);
  assert.throws(() => E.step(E.create({ budget: 0 })));
  assert.throws(() => E.step(E.create({ omission: true })));
});
