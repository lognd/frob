---
id: T-1157
title: 'gates: sys audit''s exhaustiveness pass reports every SYS205 waiver as stale
  even when check_mode_conformance correctly matches it'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_audit.py
- tests/unit/strata/test_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: regression test for the SYS205 stale-waiver exclusion fix
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass
designated_repro_test: null
threat: null
component: null
---
`frob sys audit`'s exhaustiveness/self-conformance SYSWAIVE002 stale-
waiver pass reports every SYS205:tickets_ledger waiver as stale ("no
matching SYS205:tickets_ledger finding fired this run") even though
`check_mode_conformance` (SYS205's real evaluator) correctly finds and
waives all five in the SAME `frob sys audit` run ("mode-conformance
PROVED (5 waived) -- zero UNWAIVED SYS205 gaps"). Verified pre-existing
(reproduces against a clean T-1149-landed checkout with none of T-1146's
changes applied) -- the exhaustiveness pass's own stale-waiver detection
evidently does not know about the SYS205 rule family at all, so it
always reports any SYS205 waiver as stale regardless of the real
evaluator's outcome. Found while landing T-1146; out of that ticket's
scope.