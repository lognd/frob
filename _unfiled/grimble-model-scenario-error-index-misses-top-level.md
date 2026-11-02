+++
id = "01M6DW3Z8G8RP3KH21YMX421RC"
title = "grimble-model: scenario error index misses top-level scenarios (plan_index anchor lacks file-system adoption)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T10:15:42Z"
updated = "2026-11-02T10:48:59Z"
scope = ["crates/grimble-model/src/plan_index.rs", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/tests/planning.rs"]
+++

Found while working ~EJSH114. analyze_plan keys scenarios by the file's adopting system (D157, e.g. scenario/s.sc) but PlanModel::build anchors top-level items as scenario/sc, so scenario_errors().remove(anchor) misses: error_set falls back to fails_with and collected stays empty, so PLAN006 never fires for a top-level scenario. Repro: graph.rs PLAN_BASE-style model (items after 'system s {}' at file top level) with a -!> hop. Fix: apply file_system adoption in plan_index::collect, or key both by one function.
