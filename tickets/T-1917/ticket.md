---
id: T-1917
title: 'post-land sweep regression from T-1910: 1 new error(s) (TICK002)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets.md
- src/frob/gates/_tickets_gate.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'T-1917: TICK002 must exempt a dropped-and-archived draft (residue, never
    live/referenced going forward) while still firing on a promoted-but-never-renumbered
    (done) draft'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1917: TICK002 must exempt a dropped-and-archived draft (residue, never
    live/referenced going forward) while still firing on a promoted-but-never-renumbered
    (done) draft'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
- tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
designated_repro_test: null
acceptance:
- text: TICK002 exempts a dropped-and-archived draft (residue with no live state to
    renumber out of) while still firing on a draft that reached done without ever
    being renumbered
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
- text: uv run frob check --only tickets on main's HEAD (or an equivalent on-main
    measurement) reports 0 TICK002 findings after the fix lands
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1910 at commit 5b0ca91f20f7f81c0d30aaa6a096ab3edf01dc7f found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- TICK002  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.