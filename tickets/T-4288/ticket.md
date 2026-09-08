---
id: T-4288
title: 'TestTicketArchive/TestTicketEvidence Windows failures: bare ''echo'' spawn
  fails, not a shell builtin there'
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: defect is Windows-only, unreproducible by a Linux-run mutation
    check'
  actor: logan
  at: '2026-09-08'
  old_length: 1419
  new_length: 2045
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket
- tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_silent_is_refused
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_failure_logs_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while measuring T-4278 on real Windows via winrun (not one of T-4278's own five named failures -- T-4278's total of 11 minus 3 (sibling) minus 2 (T-4155) minus 1 (T-4234) minus 5 (T-4278 itself) already accounts for the full 11, so these are NEW, previously-unmeasured failures on the current tree).

Measured on real Windows (winrun):
  tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket -- FAILED
  tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket -- FAILED

Evidence test spawns ['echo', 'verified'] as a literal executable (frob.process._guard, via --evidence-cmd 'echo verified'): 'echo' is a shell builtin on posix (works because the test's harness likely goes through a shell or a posix /bin/echo exists) but is NOT a standalone executable on Windows outside cmd.exe, so subprocess spawn fails with WinError 2 (SpawnFailed). Confirmed present independent of T-4278's own diff (reproduced against the pre-T-4278 file content too).

Needs investigation into whether the fix belongs in the test (use a real cross-platform executable, e.g. python -c 'print(1)', instead of the shell builtin 'echo') or in frob.process._guard's spawn path (shell=True or an explicit posix/win32 branch for shell-builtin commands). Not fixed here -- out of scope for T-4278, which named five specific failures and these are not among them.


frob:waive BUG002 reason="the defect is Windows-only (bare 'echo'/spawn-as-executable has no standalone binary outside cmd.exe); the designated evidence tests pass at both the parent commit and the fix on Linux (where /bin/echo exists), since this repo's mutation/repro check runs on Linux -- the platform gap that makes them fail-then-pass cannot be reproduced by a same-platform mutation check. Measured directly on the real Windows mirror instead (winrun): FAILED at parent commit 46e630521, PASSED after the fix, for both test_evidence_cmd_applied_for_docs_ticket and test_archives_done_ticket -- see the Done report."