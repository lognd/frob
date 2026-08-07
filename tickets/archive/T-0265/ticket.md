---
id: T-0265
title: self-referential frob:tests directive on a test function passes --ticket check
  but fails full DRIFT002
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: narrow speculative tests/** to the mirrored test module (T-0455 scope hygiene)
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0265 gates work is tested in tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff
designated_repro_test: null
threat: null
component: null
---
Recurring: implementer agents put a 'frob:tests <self>' directive above their own new test function; the target does not resolve as a graph qualname so full frob check fires DRIFT002, but frob check --delta --ticket (what agents+reviewers run) does NOT surface it -- so it lands and reddens main (happened for T-0213, T-0216; coordinator removed 3). Two fixes: (1) frob check --ticket should include the drift gate for edges the ticket's own diff ADDS (a new frob:tests directive in the diff must be validated even under --ticket scoping); (2) the graph should REJECT or warn on a frob:tests directive whose target is the annotated symbol itself (a test testing itself is meaningless) at directive-parse time, not silently store a dangling edge. Add a check-scoping regression + a self-edge rejection test.