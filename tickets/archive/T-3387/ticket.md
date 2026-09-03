---
id: T-3387
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3346):
  2 new (rule, file) identit(ies), 2 finding(s) (ARCH103, DOC003)'
state: dropped
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/commands/sys.md
- src/frob/app/ticket_runner/_verify.py
findings:
- - ARCH103
  - src/frob/app/ticket_runner/_verify.py
- - DOC003
  - docs/commands/sys.md
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3346) at commit a057c5e1c94eaac8538058ce55e57bd1c722ce0f found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/app/ticket_runner/_verify.py
- DOC003  docs/commands/sys.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/app/ticket_runner/_verify.py  -> attributed to T-3311 (commit 094546bc613c, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_verify.py::_reverify_direct_pytest_individually -> src/frob/app/ticket_runner/_verify.py::_run_pytest_directly -> src/frob/app/ticket_runner/_verify.py::_spawn_direct_pytest -> src/frob/app/ticket_runner/_verify.py::_python_for_tree -> src/frob/app/ticket_runner/_verify.py::_venv_python_has_frob_importable
- DOC003  docs/commands/sys.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-30 attempt 1: already resolved on main: frob check --only arch --ticket T-3387 and --only docblocks --ticket T-3387 both zero-match ARCH103/DOC003 (neither code appears in the scoped diagnostics set)

## Drop reason
- 2026-08-30: Already resolved on main: the owning gate's scoped run zero-matches every cited identity (series K measurement, 2026-08-30; T-3354's CLAUDE001 was ~/.claude materialization drift fixed by frob claude sync, no repo diff).
