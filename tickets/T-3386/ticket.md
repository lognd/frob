---
id: T-3386
title: 'Fix SELFAUDIT001: add test_check_runner.py to testsuite exec scope'
state: in-progress
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
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: adding tests/test_check_runner.py to testsuite exec via-list grows the ratchet
    count from 223 to 224; the SYS111 ratchet lock must be bumped in the same diff
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gate:SELFAUDIT reports 5 findings. Series EO diagnosed root cause fully:
design/frob.strata's testsuite node's may "exec" via [...] list (around
line 1568) is missing "tests/test_check_runner.py". That file's _git_init
fixture gained real subprocess.run call sites (lines 38/39/42/282/283)
since the strata node was last synced, so SELFAUDIT001 (checked via
_selfaudit_violations -> check_self_conformance, a full tree walk every
run, NOT diff-scoped) flags them as unaccounted exec capability use.

EO was blocked by a lease held by T-3311, which has since landed at
094546bc6 with its worktree gone -- this ticket is unblocked.

Third data point for T-3324 (live-repo conformance checks rot as
unrelated work lands).