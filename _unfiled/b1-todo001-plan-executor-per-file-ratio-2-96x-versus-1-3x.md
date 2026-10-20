+++
id = "01M5CCZCQDV53DMNJZ8W0Q305Z"
title = "B1 TODO001: plan executor per-file ratio 2.96x versus 1.3x target"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T10:16:09Z"
updated = "2026-10-20T10:16:09Z"
scope = ["crates/gob-plan/src/exec/**"]
+++

Remaining gap after ~BA2A6ST. Suspects: eval_op/Verdict::join dispatch, line_span, matcher lookups by OpId; needs a cheaper verdict representation and compiled op dispatch. Profile with perf on the b1 bench binary.
