+++
id = "01M4FD0EP322SV5ZNXD5SQT8RX"
title = "frob check writes .crunk/telemetry.jsonl into the worktree and then reports it as an opaque file (DRIFT001)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T03:58:45Z"
updated = "2026-10-09T03:58:45Z"
labels = ["adoption:hullbreach"]
scope = ["crates/crunk*/**", "crates/frob-check/**", "crates/gob-check/**", "changelog.d/**"]

[[acceptance]]
text = "Given a fresh repository, when frob check runs, then no file appears in the worktree outside .frob or gitignored state, and crunk telemetry goes to the cache dir"
bound = false
+++

Hullbreach platform repro.
