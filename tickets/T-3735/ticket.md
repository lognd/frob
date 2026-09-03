---
id: T-3735
title: fix win32 hang+failures in test_cli_doctor.py round 2
state: in-progress
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_doctor.py
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
CI run 33729699769 (windows job, AFTER T-3730 landed) still shows
tests/system/test_cli_doctor.py FFFF....FFFFFFFFFFF then a HANG. The
total-budget watchdog's inventory named
TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal
as the test in flight when the budget expired -- the test T-3730 changed
python3 -> sys.executable in, so it no longer FileNotFoundErrors, but the
spawned dead_pid_proc (inheriting stdio, unbounded .wait()) can still hang
on win32. The preceding wall of F's is very likely collateral: pytest-xdist
workers killed mid-test by the CI job's total-budget watchdog report every
in-flight/undelivered test as failed, so one true root cause (this one
unbounded subprocess wait) plausibly explains both symptoms.

Fix: give the Popen explicit DEVNULL stdio (removes any inherited-handle
risk) and bound .wait() with the same timeout=30 pattern T-3730 used for
the git subprocess calls elsewhere in this file, with a kill-then-wait
fallback so the test can never hang regardless of root cause. Also harden
TestDoctorVenvShims::test_symlink_entry_is_skipped's symlink_to() fixture
call, which requires a privilege win32 CI runners do not reliably grant,
to skip gracefully instead of erroring when unavailable.