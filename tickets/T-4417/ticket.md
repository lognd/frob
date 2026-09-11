---
id: T-4417
title: Instrument land phases with per-phase elapsed-seconds timestamps
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: high
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_phase_elapsed_logging.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_phase_elapsed_logging.py
  reason: new unit test covering the elapsed-seconds logging filter
  actor: logan
  at: '2026-09-11'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: frob:doc anchor for the new elapsed-seconds logging section
  actor: logan
  at: '2026-09-11'
evidence:
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_non_phase_log_lines_are_left_untouched
- tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_helper_starts_at_zero_on_first_call
designated_repro_test: null
acceptance:
- text: GIVEN a land runs WHEN each phase (worktree setup, graph load, gate check,
    test run, squash, sweep dispatch, etc.) starts and ends THEN the land log emits
    a line carrying that phase's elapsed seconds
  evidence:
  - tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines
- text: GIVEN this instrumentation lands WHEN a slow land is investigated THEN the
    per-phase breakdown is readable directly from the land log without needing ps
    or external profiling
  evidence:
  - tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The land log today carries no phase timestamps, so the T-4408 land's 50+ minutes could not be attributed to a specific phase without external ps inspection. Add elapsed-seconds timestamps to every phase boundary in the land log so future slow lands are diagnosable from the log alone.