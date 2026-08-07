---
id: T-0869
title: typestate cleanup-on-all-paths obligation (deinit-never-called generalized)
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
blocked_by:
- T-0868
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/arch/_typestate.py
- tests/unit/test_typestate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a fixture establishing a state then returning early on one branch without
    cleanup WHEN frob check runs THEN the cleanup-on-all-paths violation fires naming
    the leaking path
  evidence: []
- text: GIVEN a fixture releasing on every path or transferring ownership WHEN frob
    check runs THEN no violation fires
  evidence: []
threat: null
component: arch
---
T-0739 child 4 (cleanup-on-all-paths). The *_deinit-never-called class generalized: every path leaving an established state (normal return, early return, raise/throw) must destroy/release it or hand ownership off, with the child-3 excuse discharges applying. Fixture set covers early-return leaks, exception-path leaks, and conditional-establishment joins.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py