---
id: T-3977
title: frob:pending T-#### directive for spec-first red tests
state: queued
kind: feature
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tdd_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note settling the closure condition (auto-clear on ticket done
    vs a separate check) and how it interacts with DRIFT002, when this ticket's design
    step completes, then the note is attached before implementation
  evidence: []
- text: given a test carrying frob:pending T-#### where T-#### is open, when it is
    red, then it does not count as a suite regression
  evidence: []
- text: given T-#### closes and the test is still red with the directive present,
    when frob check runs, then it is flagged as a directive that must be cleared or
    the test fixed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3928 frontend-unique item. This pairs with the TDD pincer already recorded in this repo (TDD001 pushes tests first, --check-repro requires them red, DRIFT002 then fires on the red test's own directive) -- the consumer identifies the missing half: nothing distinguishes RED-BECAUSE-UNIMPLEMENTED (spec-first TDD, expected and healthy) from RED-BECAUSE-BROKEN (a real regression). Spec-first ordering currently destroys the suite's own signal, because both look identical to any gate reading pass/fail.

FINDING THIS WOULD HAVE CAUGHT: nothing in the consumer's own audits directly, but the consumer flags the risk explicitly -- a genuinely broken test and a deliberately-red spec-first test are indistinguishable to any tool watching outcome states, which weakens exactly the TDD1-DRIFT2 pincer this repo relies on for its own evidence integrity.

Proposed: a `frob:pending T-####` directive on a test, marking it expected-red until ticket T-#### lands. A gate then treats a pending test's redness as expected (does not count as a suite regression) while still requiring it to flip green (or the directive removed) once its ticket closes -- otherwise it is exactly a no-exit waiver in test-directive form. Design the closure condition (auto-clear on ticket done? separate check?) before implementing.
