---
id: T-3447
title: 'SYS111 ratchet: core fs.read via-list grew to 35 sites, failing test_sys_gate_zero_violations'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-ratchet.lock.json
- docs/design/registry/capability-via-ratchet.lock.json
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: the real SYS111 capability-ratchet lock file this ticket must edit -- the
    originally declared frob-ratchet.lock.json is an unrelated ratchet with no core/testsuite
    entries
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: design/frob.strata
  reason: T-3447's own fix touches only docs/design/registry/capability-via-ratchet.lock.json
    (the SYS111 ratchet ceilings) -- it never edits design/frob.strata itself, so
    releasing this lease frees it for T-3450's SYS100 fix, which does need to edit
    design/frob.strata
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/system/test_frob_self_model.py
  reason: T-3450 needs a brief lease on this file to add a narrow SYS100 regression
    test (existing test_fragments_module_fs_read_is_declared_not_selfaudit001 precedent);
    T-3447's own diff never edits this file, only docs/design/registry/capability-via-ratchet.lock.json,
    so releasing is safe -- T-3447 will re-verify with the shared node id directly
    at land time without needing to hold a write lease on it
  actor: logan
  at: '2026-08-29'
- op: add
  glob: design/frob.strata
  reason: T-3450 landed and released the lease -- restoring for re-measuring the SYS111
    ratchet counts, which shifted after T-3450's own via-list addition
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: explain the block-on-T-3450 decision
  actor: logan
  at: '2026-08-29'
  old_length: 1008
  new_length: 2323
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
    SELFAUDIT001: self-audit family SYS111 node=core: fs.read via-list on core grew to 35 site(s) ...
The SYS111 growth ratchet on the core node fs.read via-list tripped after T-3416/T-3409/T-3429/T-3430 added sites. Read the SYS111 doctrine in docs/ (git grep SYS111 -- docs) and apply the sanctioned resolution: either re-baseline the ratchet with a recorded reason, or move sites off the core node. Do not waive. Verify test_sys_gate_zero_violations passes.


## Status note (not a Done report -- ticket blocked, not closed)

T-3447's own SYS111 capability-ratchet breach is fully fixed: all 5 breaches
(core::fs.read 34->35, testsuite::env.read 16->17, testsuite::exec 224->225,
testsuite::fs.read 171->172, testsuite::fs.write 405->407) re-baselined in
docs/design/registry/capability-via-ratchet.lock.json with recorded reasons,
per the "do not waive, re-baseline or move sites off the node" instruction.
Verified 0 SYS111/capability-ratchet warnings remain in a fresh run.

However the specified verification command (test_sys_gate_zero_violations)
also requires 0 SYS100 violations repo-wide, and 10 pre-existing SYS100
findings (tests/unit/test_check_admission.py:373/374/375/377/378/406/412/
435/441/500 -- exec capability observed but not declared in design/frob.strata's
testsuite node) are a different, unrelated defect that blocks the same test
from going green. This is out of T-3447's declared scope (design/frob.strata,
frob-ratchet.lock.json, tests/system/test_frob_self_model.py, plus
docs/design/registry/capability-via-ratchet.lock.json added for the SYS111
fix itself) -- fixing it here would be silent scope expansion onto an
unrelated finding. Filed T-3450 for it and blocking this ticket on it rather
than force-closing against a red acceptance test.

## Unblock log
- 2026-08-29: unblocked by T-3450 -- T-3450 landed at a58cacf5d656db852617e2d2dd132f019b77cac0 (SYS100 fix); merged main into this worktree, re-measured SYS111 ratchet counts (testsuite::exec now 226, +1 from T-3450's own via-list addition), bumped the ceiling accordingly, and confirmed test_sys_gate_zero_violations now passes