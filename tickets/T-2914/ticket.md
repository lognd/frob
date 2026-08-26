---
id: T-2914
title: 'WIRE002: T-2645''s WIRE001 waiver on _unlanded.py::_remove_scratch_file missing
  follow_up'
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_unlanded.py
evidence_scope:
- tests/unit/test_unlanded_branch_work.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-2914 is a WIRE001 waiver metadata fix with no runtime behavior delta;
    BUG002 needs the no-behavior-change directive to accept confirmatory-only evidence
  actor: logan
  at: '2026-08-25'
  old_length: 692
  new_length: 912
evidence:
- tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2645 landed a `frob:waive WIRE001` on `_unlanded.py::_remove_scratch_file`
without a `follow_up="T-####"` attribute -- WIRE002 now flags it repo-wide
(discovered while running `frob check --ticket T-2646`, an unrelated
ticket; this file is not in T-2646's scope, hence filing rather than
fixing in place).

Fix: add `follow_up="T-####"` to the existing WIRE001 waiver at
src/frob/tickets/_unlanded.py near line 508 (or reconsider whether an
atexit.register-only callback should carry the simpler "permanent"-style
waiver shape a couple of other WIRE001 waivers in this repo use, if that
pattern applies here -- check src/frob/gates/_waive.py's own WIRE001
waiver-shape documentation first).

frob:no-behavior-change reason="one-line frob:waive WIRE001 attribute addition (adding follow_up=) -- no runtime behavior change, only a lint-directive metadata fix; nothing to reproduce as a failing-then-passing test"