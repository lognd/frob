---
id: T-1901
title: 'post-land sweep regression from T-1892: 1 new error(s) (SYS004)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
blocked_by:
- T-1900
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1892 at commit c8e50a3d878dad4f2de2634ae2ebd3b41235fbb1 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- SYS004  design/frob.strata

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SYS004  design/frob.strata  -> attributed to T-1892 (commit c8e50a3d878d, already closed/dropped -- filed below) via design/frob.strata::frob.claude_hooks

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="the SYS004 corruption this ticket describes was already hand-repaired directly on main in e1a603603e101abb08e624517f3ba72d9c14fcda (\"fix(design): final repair of strata corruption before T-1900's fix takes effect\"), which predates this ticket being picked up and is not associated with any ticket id. The designated repro test genuinely FAILED at e1a603603's own parent (67894869e9366977fad805b0f50c2b3af493e0a2, verified via frob ticket evidence T-1901 --check-repro ... --base-ref e1a603603~1) -- a real repro exists -- but by the time this land runs, main's own tip already contains the fix, so the same test necessarily PASSES at land-time's parent too and BUG002's land-time check cannot distinguish that from confirmatory-only evidence. This is the documented ledger/doc-correction shape: no code change is landing under this ticket id, only recording that the fix (which did happen, and was verified to genuinely reproduce-then-fix) is attributed and closed out."