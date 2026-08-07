---
id: T-1577
title: 'WAIVE004: exempt diff-scoped rules (WIRE001, SCOPE001, audit DEPR005/DEAD001)
  from full-run staleness reads'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_fix_engine.py
  reason: this ticket's actual fix lives entirely in _waive.py -- _fix_engine.py was
    listed in the original ticket scope but is not touched here; narrowing avoids
    pulling in that file's whole-file SCOPE002 doc-anchor closure (gates_e501_autofix.md/tickets.md)
    which belongs to a different ticket's edits
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_exempts_diff_scoped_rules[wire001]
- tests/test_gates.py::TestTestGate::test_waive004_exempts_diff_scoped_rules[scope001]
designated_repro_test: null
threat: null
component: null
---
WIRE001 is diff-scoped by construction (src/frob/gates/_wire.py: 'a newly-added symbol' -- it can only fire against a ticket diff). On a full unscoped run it produces ZERO findings structurally, so ALL WIRE001 waivers read 'matches 0 findings' forever: 62 bogus WAIVE004 warnings on main today, plus ~40 more per land log. SCOPE001 is likewise diff-bound (_waive.py:1092 already documents it as 'a diff-scoped rule like SCOPE001'). T-1064 built the exact mechanism for this (_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES) but only enrolled INV006/DUP001/DUP002/AFFECT001/AFFECT002.

Fix: enroll WIRE001 and SCOPE001; audit DEPR005, DEAD001, REF002 for the same shape and enroll any that qualify. Each enrollment needs a one-line justification comment citing the gate's own diff-scoping. Expected effect: roughly 80 of the 98 standing WAIVE004 warnings on main disappear, and the per-land WAIVE004 noise drops proportionally.