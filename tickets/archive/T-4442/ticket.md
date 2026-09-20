---
id: T-4442
title: 'Windows: land phase elapsed prefix reads 0.0 twice, monotonic test fails on
  the CI runner clock'
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_phase_elapsed_logging.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 confirmatory-only refusal at land: the bug is only observable on
    the Windows runner clock, same shape as T-4404/T-4430'
  actor: logan
  at: '2026-09-12'
  old_length: 1145
  new_length: 1843
evidence:
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_non_phase_log_lines_are_left_untouched
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_helper_starts_at_zero_on_first_call
designated_repro_test: tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34675057655 (head d0fc8ba1e, 2026-09-12), Windows leg only. Node id: tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines. Assertion: assert second_elapsed > first_elapsed -> assert 0.0 > 0.0. The test sleeps 0.05s between two phase lines and expects the [+N.Ns] prefix (src/frob/app/ticket_runner/_land_cmd.py:176, T-4417) to advance. On the GitHub Windows runner both prefixes read 0.0: either the elapsed clock has ~15.6ms tick granularity on win32 (time.time), or the one-decimal formatting rounds 0.05s to 0.0 on both lines and the strict greater-than only passes on POSIX where the sleep overshoots. Passes on ubuntu and macOS in the same run. ACCEPTANCE: (1) the elapsed clock uses time.perf_counter (monotonic, sub-ms on win32); (2) the test asserts monotonic non-decrease with a sleep long enough to move the one-decimal prefix (at least 0.2s) or asserts on the raw float via the record attribute rather than the formatted prefix; (3) measured passing on the winrun mirror AND the reasoning covers the runner's clock. Sprint v0.531.0 (CI green blocker).

frob:waive BUG002 reason="the defect is win32-only (time.monotonic tick granularity of ~15.6ms on the GitHub Windows runner makes two phase lines 50ms apart both format as [+0.0s]); check-repro runs the designated test at the parent commit on this (Linux) host, where monotonic already has sub-millisecond resolution, so the test passes at the parent by construction. Measured on the winrun Windows mirror and in CI run 34675057655 / 34708801531 (Windows leg): the node id tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines fails before the fix (assert 0.0 > 0.0) and passes after (perf_counter clock, 0.25s spacing)."