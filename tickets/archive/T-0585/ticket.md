---
id: T-0585
title: 'INV006 first-turn-on pool: ~167 source-side exclusivity claims need disposition
  (bind invariant / reword / waive)'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_logging_module.py::test_should_color_respects_no_color
- tests/unit/test_logging_module.py::test_should_color_respects_force_color
- tests/unit/test_logging_module.py::test_should_color_no_color_wins_over_force_color
- tests/unit/test_logging_module.py::test_should_color_term_dumb_disables_color_on_a_tty
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_nested_calls_restore_after_outermost_exits
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_interleaved_enter_exit_across_threads_never_sticks
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_threaded_stress_always_restores
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_single_call_still_quiets_and_restores
- tests/test_secrets_gate.py::TestRedact::test_never_returns_the_token
- tests/unit/test_render.py::TestElementsPlainShapeInvariant::test_heading_subhead_shape_stable_under_color
- tests/unit/test_render.py::TestElementsPlainShapeInvariant::test_kv_row_shape_stable_under_color
- tests/unit/test_render.py::TestElementsPlainShapeInvariant::test_count_summary_shape_stable_under_color
designated_repro_test: null
threat: null
component: null
---
T-0408 landed INV006 warn-first over src/, strata-core/src/, frob-core/src/ with ~167 undispositioned findings (disclosed prose cut, no ticket -- filed here). Same calibrate-then-burndown discipline as the INV003/T-0520 campaign: bucket by file/pattern first, calibrate further if a noise class dominates, then bind real invariants, reword overclaims, or waive genuine-design-intent with reasons. Candidate for the T-0569 ratchet-pool mechanism once it lands. Scope: src/frob/gates/invariants.py, invariants/, the flagged source files.