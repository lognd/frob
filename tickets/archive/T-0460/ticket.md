---
id: T-0460
title: 'render vocabulary: table, tree, progress (TTY-only clears-on-completion, T-0419
  contract), count-deltas elements on RenderWriter (T-0448 follow-on)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/render/
- docs/modules/render.md
- tests/unit/test_render.py
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_render.py
  reason: T-0460 render work maps to tests/test_render.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/test_render.py
  reason: 'T-0460: main merge moved the render test suite to tests/unit/test_render.py;
    the top-level path never existed post-merge'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_render.py
  reason: 'T-0460: main merge moved the render test suite to tests/unit/test_render.py;
    the top-level path never existed post-merge'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'T-0460: REL001 requires a version bump + changelog entry for the new public
    render.py symbols (table/tree/count_deltas/Progress)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'T-0460: REL001 requires a version bump + changelog entry for the new public
    render.py symbols (table/tree/count_deltas/Progress)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'T-0460: uv.lock self-pin drifts to match pyproject.toml''s version bump
    on any uv run'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_table_plain_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_table_color_paints_header_and_rule_only
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_tree_plain_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_tree_color_paints_only_depth_zero
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_plain_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_positive_delta_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_has_no_ansi_in_plain
- tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_table
- tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_tree
- tests/unit/test_render.py::TestWriterTableTreeCountDeltas::test_write_count_deltas
- tests/unit/test_render.py::TestProgress::test_progress_updates_in_place_on_tty
- tests/unit/test_render.py::TestProgress::test_progress_is_noop_on_non_tty
- tests/unit/test_render.py::TestProgress::test_progress_clear_erases_the_line_on_tty
- tests/unit/test_render.py::TestProgress::test_progress_clear_is_noop_on_non_tty
- tests/unit/test_render.py::TestProgress::test_progress_context_manager_clears_on_exit
- tests/unit/test_render.py::TestProgress::test_progress_context_manager_clears_even_on_exception
- tests/unit/test_render.py::TestProgress::test_progress_shorter_next_line_pads_over_stale_tail
designated_repro_test: null
threat: null
component: null
---
