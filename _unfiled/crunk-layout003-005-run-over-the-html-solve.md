+++
id = "01M7EXSFWBE6NF7KTA3R2C2421"
title = "crunk LAYOUT003-005: run over the html solve"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:54Z"
updated = "2026-11-15T06:19:54Z"
idempotency_key = "crunkplan-f7c6e6b1ad54"
labels = ["no-story"]

[[acceptance]]
text = "LAYOUT003-005 fire on a .scene.html fixture (tests)"
bound = false

[[acceptance]]
text = "the legacy solver has no remaining caller"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H8.
Evidence: LAYOUT003-005 read the legacy .scene.json mini-solver (fixed CHAR_WIDTH_EM) rather than the html solve
Remedy: port them to the html (taffy+parley) solve; retire crunk-ingest::scene::solve_scene. Grimble M2 overlap.
Crates/files: crates/crunk-rules/src/scene_files.rs, crates/crunk-ingest/src/scene/solve.rs
Verify against HEAD first; the audit ran on a stale binary.
