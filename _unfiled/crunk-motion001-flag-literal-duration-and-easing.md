+++
id = "01M7EXTD295PMAAEC9R74DKBAW"
title = "crunk MOTION001: flag literal duration and easing"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:23Z"
updated = "2026-11-15T06:20:23Z"
idempotency_key = "crunkplan-0fc75ec8bf8c"
labels = ["no-story"]

[[acceptance]]
text = "a literal 200ms in a transition raises MOTION001"
bound = false

[[acceptance]]
text = "a token reference passes"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M3.
Evidence: literal durations and easings pass MOTION001
Remedy: require motion tokens
Crates/files: crates/crunk-rules motion
Verify against HEAD first; the audit ran on a stale binary.
