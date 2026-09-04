---
id: T-3790
title: fix win32 test_fix_engine scope-lease/tier-a failures
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/fix/*.py tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only newline-translation defect, cannot repro on Linux
    CI'
  actor: logan
  at: '2026-09-04'
  old_length: 279
  new_length: 1055
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert and TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content fail. Root cause TBD via winrun. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; the tests wrote fixture content with a bare text-mode write_text(), which translates \n to os.linesep on write (\r\n on win32), then compared _snapshot_dirty_files's raw on-disk bytes against an LF-only literal -- on Linux os.linesep is already \n so the pre-fix test also passed at the parent commit, but on win32 the write introduced CRLF bytes the comparison never expected. Fixed by adding newline=\"\" to the fixture writes so the on-disk bytes are LF regardless of platform, matching what the production _snapshot_dirty_files (which reads raw bytes verbatim, correctly) would see for an LF-authored file. No Linux-repro-at-parent-commit test can demonstrate a win32-only newline-translation mismatch."