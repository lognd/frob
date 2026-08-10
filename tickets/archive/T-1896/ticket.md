---
id: T-1896
title: 'post-land sweep regression from T-1872: 1 new error(s) (invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/gates/test_sys_interface_canonical_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1872 at commit d241bcd7201cc3250e7b9205a4776a93e7de5da6 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py  -> attributed to T-1872 (commit d241bcd7201c, already closed/dropped -- filed below) via tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
frob:no-behavior-change reason="The diff is confined to three test call sites that passed None into fix_sys_interface_canonical_order's non-Optional snapshot parameter; the fix constructs a minimal unused GraphSnapshot instead. The production signature is untouched and the real caller in _fix_engine.py already passes a genuine snapshot. There is no runtime-observable difference at the parent commit, so BUG002's fail-then-pass proof is unavailable by construction -- the proof is the ty gate no longer reporting invalid-argument-type at these three sites."
