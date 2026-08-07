---
id: T-1277
title: 'TEST005 burn-down: src/frob/render (42 findings, 36 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/render/**
- tests/render/**
- tests/unit/test_render.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_render.py
  reason: package's real test file lives at tests/unit/test_render.py per existing
    convention; tests/render/** in the original scope does not exist
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_render.py::TestRenderer::test_write_methods_emit_one_line_each
- tests/unit/test_render.py::TestRenderer::test_for_stream_resolves_color_once
- tests/unit/test_render.py::TestRenderer::test_line_emits_text_verbatim
- tests/unit/test_render.py::TestRenderer::test_write_good
- tests/unit/test_render.py::TestRenderer::test_write_good_color_wraps_in_ansi
- tests/unit/test_render.py::TestRenderer::test_write_warn
- tests/unit/test_render.py::TestRenderer::test_write_warn_color_wraps_in_ansi
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_plain_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_positive_delta_shape
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_has_no_ansi_in_plain
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_positive_delta_paints_critical
- tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_zero_delta_paints_muted
designated_repro_test: null
acceptance:
- text: GIVEN the render package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/render/**
  evidence:
  - tests/unit/test_render.py::TestRenderer::test_write_methods_emit_one_line_each
- text: GIVEN a 0.0%-branch symbol in render WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_render.py::TestRenderer::test_for_stream_resolves_color_once
- text: GIVEN a new test added to close a render TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_render.py::TestRenderer::test_line_emits_text_verbatim
  - tests/unit/test_render.py::TestTableTreeCountDeltas::test_count_deltas_color_positive_delta_paints_critical
threat: null
component: null
---
Package: src/frob/render (or the listed root modules).
TEST005 findings at current baseline: 42 total, 36 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_elements.py :: heading
_elements.py :: subhead
_elements.py :: kv_row
_elements.py :: status_pill
_elements.py :: count_summary
_elements.py :: path_label
_elements.py :: ticket_id_label
_elements.py :: table
_elements.py :: tree
_elements.py :: count_deltas
_renderer.py :: Progress.update
_renderer.py :: Progress.clear
_renderer.py :: RenderWriter.heading
_renderer.py :: RenderWriter.subhead
_renderer.py :: RenderWriter.kv
_renderer.py :: RenderWriter.status
_renderer.py :: RenderWriter.count_summary
_renderer.py :: RenderWriter.path
_renderer.py :: RenderWriter.ticket_id
_renderer.py :: RenderWriter.good
_renderer.py :: RenderWriter.warn
_renderer.py :: RenderWriter.critical
_renderer.py :: RenderWriter.muted
_renderer.py :: RenderWriter.table
_renderer.py :: RenderWriter.tree
_renderer.py :: RenderWriter.count_deltas
_renderer.py :: RenderWriter.progress
_renderer.py :: Renderer.for_stream
_renderer.py :: Renderer.blank
_renderer.py :: Renderer.line
_color.py :: resolve_color
_palette.py :: good
_palette.py :: warn
_palette.py :: critical
_palette.py :: muted
_palette.py :: accent

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.