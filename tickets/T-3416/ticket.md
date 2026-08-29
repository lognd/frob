---
id: T-3416
title: Update design/frob.strata SYS100 fs.read capability for process/_reap split
  (T-3396)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations`
fails on main independent of T-3350/T-3413's nodeid.py regression (measured after
T-3413's fix was applied but not yet landed, caches cleared, no REPLAY):

  SELFAUDIT001 (SYS100, node=core): fs.read observed but not declared
      src/frob/process/_proc_scan.py:82
      src/frob/process/_proc_scan.py:134
      src/frob/process/_proc_scan.py:186
      src/frob/process/_proc_scan.py:227
      src/frob/process/_proc_scan.py:403

A sixth, closely related finding for src/frob/stats/_agentic_shared.py:42 is
ALREADY tracked at T-3409 (queued) -- do not duplicate that one here, only
the src/frob/process/_proc_scan.py side is new.

src/frob/process/_proc_scan.py traces to T-3396 (already closed/landed),
which split src/frob/process/_reap.py under LARGE001's 800-line threshold
and produced _proc_scan.py as a sibling module. Same shape as T-3409 and as
T-3350/T-3413's own root cause: a module split moved fs.read-performing code
into a new file whose design-model capability declaration (`may "fs.read"
via ...` on the `core` node) was never updated to include it.

Filed separately from T-3413 because it predates T-3350 and is caused by a
different, unrelated ticket (T-3396) -- not a T-3350 regression.
`tickets/T-3388/ticket.md`'s `frob:waive BUG002 ... follow_up="T-3413"`
clause names `test_sys_gate_zero_violations` as confounded specifically by
T-3350's regression; T-3413 fixes that half, but THIS ticket (plus T-3409)
is the other half still keeping that test red, so T-3388's waiver should
not be cleared until both are fixed.

Fix direction: add `src/frob/process/_proc_scan.py` to `core`'s
`may "fs.read" via ...` declaration in design/frob.strata (mirroring the
existing declaration for its sibling files in the same node), then
re-measure `test_sys_gate_zero_violations` clean (together with T-3409's
fix for the _agentic_shared.py side).
