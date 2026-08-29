---
id: T-3386
title: 'Fix SELFAUDIT001: add test_check_runner.py to testsuite exec scope'
state: done
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
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): T-3386 is a design/frob.strata + ratchet-lock
    declaration sync: tests/test_check_runner.py''s _git_init fixture already called
    subprocess.run before this ticket; this ticket only teaches the strata model and
    its ratchet lock about pre-existing, unchanged runtime behavior. No src/frob code
    path changes.'
  actor: logan
  at: '2026-08-29'
  old_length: 718
  new_length: 1055
- mode: append
  reason: 'BUG002 front door (T-2393): T-3386 is a design/frob.strata + ratchet-lock
    declaration sync: tests/test_check_runner.py''s _git_init fixture already called
    subprocess.run before this ticket; this ticket only teaches the strata model and
    its ratchet lock about pre-existing, unchanged runtime behavior. No src/frob code
    path changes.'
  actor: logan
  at: '2026-08-29'
  old_length: 1055
  new_length: 1392
evidence:
- tests/unit/gates/test_sys_selfaudit.py::TestSelfauditSeverity::test_sys107_defaults_to_warn
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 541e91184b93e2590254f212057b7e74715e6932
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

frob:no-behavior-change reason="T-3386 is a design/frob.strata + ratchet-lock declaration sync: tests/test_check_runner.py's _git_init fixture already called subprocess.run before this ticket; this ticket only teaches the strata model and its ratchet lock about pre-existing, unchanged runtime behavior. No src/frob code path changes."

frob:no-behavior-change reason="T-3386 is a design/frob.strata + ratchet-lock declaration sync: tests/test_check_runner.py's _git_init fixture already called subprocess.run before this ticket; this ticket only teaches the strata model and its ratchet lock about pre-existing, unchanged runtime behavior. No src/frob code path changes."