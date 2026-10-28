+++
id = "01M5CCZCYB5QYV8ZKN84E3SVYY"
title = "B1 DOC002: plan executor per-file ratio 6.57x versus 1.3x target"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T10:16:09Z"
updated = "2026-10-28T12:55:42Z"
labels = ["no-story"]
scope = ["crates/gob-plan/src/exec/**"]
+++

Remaining gap after ~BA2A6ST. Suspects: link_dest, resolve_path joins, attribute lookups. Profile with perf on the b1 bench binary.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
