---
id: T-2935
title: Delete _sync_may.py's dead SYS100 auto-widening functions
state: done
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: T-2920
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_sync_may.py
- src/frob/strata/_shrink.py
- tests/unit/strata/test_sync_may.py
- tests/unit/strata/test_shrink.py
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_sync_may.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/strata/_shrink.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_sync_may.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_shrink.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: matches the already-committed T-2920 cleanup work this ticket now tracks
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2920
  reason: 'child of the T-2920 shrink-only ratchet epic: deletes the last dead widening
    code the epic''s own acceptance criteria depend on'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early
- tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_widening_functions_no_longer_exist_in_sync_may
- tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_no_module_under_src_frob_defines_or_imports_a_widening_function
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2922 unwired the only caller of frob.strata._sync_may's SYS100 core+
extended may= auto-widening writer (sync_may_report/apply_sync_may/
sync_may_extended_report/apply_sync_may_extended/WholeNodeMayGrantDiff),
deliberately leaving the functions themselves in place for one commit to
avoid an ImportError racing T-2920's own concurrent work.

This ticket does the deferred cleanup: confirm zero remaining importers
repo-wide, delete the dead functions, and extend T-2923's own
deliberately-scoped no-widening-path proof (which explicitly disclosed
it could not yet prove the epic-wide "no auto-widening path exists
anywhere" property, since the widening functions still existed at the
time) to a real repo-wide test.

Filed directly under T-2920 rather than folded into the epic's own
ticket record, so the epic's state accurately reflects that T-2910/
T-2911 (its other two named child tickets) are not yet done -- this
piece can close on its own regardless of when those two finish.