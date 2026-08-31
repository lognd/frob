---
id: T-3539
title: Cplace symref/file uses os.sep via str(path) instead of posix -- fails on Windows
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_comment_placement.py
- tests/gates/test_comment_placement.py
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates/test_comment_placement.py
  reason: must-fire PureWindowsPath fixture lives here
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: AFFECT001 requires a doc touch at the comment-placement anchor for the os.sep
    fix
  actor: logan
  at: '2026-08-31'
body_changes:
- mode: append
  reason: BUG002 tooling cannot check-repro a brand-new test against a not-yet-committed
    parent
  actor: logan
  at: '2026-08-31'
  old_length: 1646
  new_length: 2435
evidence:
- tests/gates/test_comment_placement.py::TestCplace001::test_symref_binds_to_the_enclosing_function
- tests/gates/test_comment_placement.py::TestCplace002::test_must_stay_quiet_exempt_path
- tests/gates/test_comment_placement.py::TestCplace001::test_must_stay_quiet_exempt_path
- tests/gates/test_comment_placement.py::TestCplace001::test_symref_stays_posix_joined_on_a_windows_shaped_path
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3511 (Windows CI re-measurement): tests/gates/test_comment_placement.py::TestCplace001::test_symref_binds_to_the_enclosing_function fails on windows-latest -- AssertionError: assert 'src\\frob\\x.py::handler' == 'src/frob/x.py::handler'. Root cause: src/frob/gates/_comment_placement.py:179 and :278 both do `rel = str(path)` and then build the Violation's `symref`/`file` as f"{rel}::{symbol}" (line 205) -- `str(path)` on a `pathlib.Path` uses the platform's native separator (`os.sep`), so on Windows the same input `Path("src/frob/x.py")` stringifies with backslashes, breaking the symref's cross-platform forward-slash-joined convention every other part of this graph (frob:tests/frob:doc directive targets, waiver matching) assumes is forward-slash-joined.

FIX: posix-normalize at both `rel = str(path)` sites (src/frob/gates/_comment_placement.py:179, :278) -- e.g. `rel = path.as_posix()` (a `pathlib.PurePath` method that always uses `/`, regardless of platform) instead of `str(path)`. Verify with a Windows-shaped input (a `Path` built from backslash-separated components, or a positive-control test that fails without the fix) that the resulting `rel`/`symref` stay forward-slash-joined -- the two failing tests (test_symref_binds_to_the_enclosing_function, and TestCplace001/TestCplace002's test_must_stay_quiet_exempt_path, which uses the same `rel` build for `file=`) should then pass on windows-latest.

Filed under T-3505 (Windows portability epic) -- CPLACE001/CPLACE002 are gates for the comment-placement rules (T-2987/T-2994), unrelated to the five T-3505 primitive fixes, so this is a leaf of its own.



frob:waive BUG002 reason="manually verified the genuine repro before landing: with src/frob/gates/_comment_placement.py's rel = path.as_posix() reverted back to rel = str(path) (the exact pre-fix code), tests/gates/test_comment_placement.py::TestCplace001::test_symref_stays_posix_joined_on_a_windows_shaped_path FAILS (AssertionError: src\\\\frob\\\\x.py != src/frob/x.py) -- restoring the fix makes it pass. frob ticket evidence --designate-repro/--check-repro cannot itself confirm this pre-land (the test is new, so no commit in this worktree's own history yet contains it without the fix to diff against, and post-land squashing means no ref in main history ever will either, per T-2025's own documented limitation) -- this manual before/after run is the equivalent verification."