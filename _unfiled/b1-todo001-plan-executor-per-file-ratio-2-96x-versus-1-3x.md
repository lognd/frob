+++
id = "01M5CCZCQDV53DMNJZ8W0Q305Z"
title = "B1 TODO001: plan executor per-file ratio 2.96x versus 1.3x target"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T10:16:09Z"
updated = "2026-11-09T19:26:46Z"
labels = ["no-story"]
scope = ["crates/gob-plan/src/exec/**", "crates/gob-plan/src/exec/core/eval.rs", "crates/gob-plan/src/exec/core/mod.rs"]
+++

Remaining gap after ~BA2A6ST. Suspects: eval_op/Verdict::join dispatch, line_span, matcher lookups by OpId; needs a cheaper verdict representation and compiled op dispatch. Profile with perf on the b1 bench binary.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
