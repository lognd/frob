---
id: T-2171
title: 'post-land sweep regression from T-2157, T-2155: 3 new (rule, file) identit(ies),
  3 finding(s) (ARCH103, COV001, TEST001)'
state: queued
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_git_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2157, T-2155 at commit 8379e92fff856f88a8d7ec2e3781a077797a24a6 found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/tickets/_land_git_ops.py
- COV001  src/frob/tickets/_land_git_ops.py
- TEST001  src/frob/tickets/_land_git_ops.py

T-2009: 2 lands (T-2157, T-2155) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2157, T-2155 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/tickets/_land_git_ops.py  -> attributed to T-2157 (commit 76f94bccbcd1, already closed/dropped -- filed below) via src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue -> src/frob/tickets/_land_git_ops.py::_verified_reset_root -> src/frob/tickets/_land_git_ops.py::_refuse_drift_but_unstage -> src/frob/tickets/_land_git_ops.py::_unstage_index_only
- COV001  src/frob/tickets/_land_git_ops.py  -> attributed to T-2157 (commit 76f94bccbcd1, already closed/dropped -- filed below) via src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue -> src/frob/tickets/_land_git_ops.py::_verified_reset_root -> src/frob/tickets/_land_git_ops.py::_refuse_drift_but_unstage -> src/frob/tickets/_land_git_ops.py::_unstage_index_only
- TEST001  src/frob/tickets/_land_git_ops.py  -> attributed to T-2157 (commit 76f94bccbcd1, already closed/dropped -- filed below) via src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue -> src/frob/tickets/_land_git_ops.py::_verified_reset_root -> src/frob/tickets/_land_git_ops.py::_refuse_drift_but_unstage -> src/frob/tickets/_land_git_ops.py::_unstage_index_only

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.