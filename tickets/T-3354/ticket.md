---
id: T-3354
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3344):
  1 new (rule, file) identit(ies), 1 finding(s) (CLAUDE001)'
state: queued
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
- .claude/hooks/sync-claude-config.py
findings:
- - CLAUDE001
  - .claude/hooks/sync-claude-config.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3344) at commit f9e77b4181e635fa38ca70be214fdb699792d896 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py  -> attributed to T-3288 (commit 428321e76f87, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_land_cmd.py::_finish_land_after_success -> src/frob/app/ticket_runner/_land_cmd.py::_print_land_proof -> src/frob/app/ticket_runner/_land_cmd.py::_land -> src/frob/app/ticket_runner/_land_cmd.py::_land_core -> src/frob/app/ticket_runner/_land_cmd.py::_land_core_prepare -> src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land -> src/frob/app/ticket_runner/_land_cmd.py::_ruff_baseline_diagnostic_identities -> src/frob/app/ticket_runner/_land_cmd.py::_ruff_diagnostic_identity
- OPAQUE001  tests/unit/test_land_finish_idempotent.py  -> attributed to T-3288 (commit 428321e76f87, already closed/dropped -- filed below) via tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded
- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-30 attempt 1: no repo code change applies: CLAUDE001 was live environment drift (managed ~/.claude/hooks/root-write-guard.py copy stale vs .claude/hooks/root-write-guard.py source) reconciled via 'frob claude sync' (writes only to ~/.claude, outside the repo); re-verified clean with frob check --only gates-fast --ticket T-3354 (no CLAUDE001 in the result set)
