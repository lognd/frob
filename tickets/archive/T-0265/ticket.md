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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 806
  new_length: 1881
evidence:
- tests/gates_suite/test_prework.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Recurring: implementer agents put a 'frob:tests <self>' directive above their own new test function; the target does not resolve as a graph qualname so full frob check fires DRIFT002, but frob check --delta --ticket (what agents+reviewers run) does NOT surface it -- so it lands and reddens main (happened for T-0213, T-0216; coordinator removed 3). Two fixes: (1) frob check --ticket should include the drift gate for edges the ticket's own diff ADDS (a new frob:tests directive in the diff must be validated even under --ticket scoping); (2) the graph should REJECT or warn on a frob:tests directive whose target is the annotated symbol itself (a test testing itself is meaningless) at directive-parse time, not silently store a dangling edge. Add a check-scoping regression + a self-edge rejection test.

<!-- narrative-moved:src/frob/graph/dsl.py:1406:T-0265 -->
T-0265: a literal self-referential `frob:tests` directive (target ==
src) is NOT rejected here -- it is this repo's own widespread,
deliberate convention for a test function to name itself as its own
evidence anchor (see e.g. every `TestDebtGate`/`TestDeprecatedGate`
method in tests/test_gates.py, and `TestTest010KindValidation.
test_dangling_tests_endpoint_still_caught_by_drift002`'s own
docstring: a `frob:tests` edge whose CODE-side endpoint no longer
resolves is already caught by the existing, edge-kind-agnostic
DRIFT002 mechanism, no TESTS-specific parse-time rejection needed).
T-0265's actual bug is a MISMATCHED-convention self-reference (the
directive's target string uses pytest's `Class::method` collect-only
separator while the graph's own qualname is `Class.method`, so the
two strings differ and the edge is genuinely dangling) slipping past
a ticket-scoped check that never evaluates `drift` at all -- fixed in
`frob.gates._build_jobs` (drift now always runs), not by rejecting
directives here.