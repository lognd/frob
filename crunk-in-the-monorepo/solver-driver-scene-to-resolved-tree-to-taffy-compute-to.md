+++
id = "01M5XCWYB9M2YSJ5EGABMREX1B"
title = "Solver driver: scene to resolved tree to taffy compute to layout-solve JSON, deterministic across runs"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-27T00:41:54Z"
updated = "2026-10-27T00:41:54Z"
labels = ["area:crunk"]
scope = ["crates/crunk-layout/src/solve/**, crates/crunk-layout/tests/solve*.rs"]

[[acceptance]]
text = "Given a scene, when solved twice, then the outputs are byte-identical. Edge cases: a scene with a duplicate or missing data-id is refused with SCENE002 context not solved; an unknown component tag lays out as an empty block with a note; a viewport of 0x0 returns zero-size boxes without panic; a root taller than the viewport reports page overflow; deeply nested trees (depth 200) do not overflow the stack; two viewports (breakpoints) of one scene are solved independently; nodes with identical positions keep document order; solve of an unchanged scene after a token edit that does not touch it is unchanged"
bound = false
+++

Design crunk.md section 3. Glue ticket: consumes the style, text and output modules. Public entry point solve_scene_html(scene, tokens, viewport, fonts) -> Result<LayoutSolveDoc, SolveError>.
