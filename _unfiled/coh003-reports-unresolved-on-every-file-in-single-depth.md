+++
id = "01M5M34XTDZEZ08TAA78872RRP"
title = "COH003 reports Unresolved on every file in single-depth repos with no layered model"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-23T09:58:20Z"
updated = "2026-10-23T10:37:47Z"
scope = ["crates/grimble-check/**", "docs/design/**", "docs/reference/rules/**", "Cargo.lock"]

[[acceptance]]
text = "External callees (not resolved to any repo file) are excluded from COH003 layer judgement and never produce Unresolved"
bound = true

[[acceptance]]
text = "A single-depth repo with no layered model yields at most one repo-level COH003 Unresolved note, not one per file"
bound = false
+++

Found while working 62Y1A18: with no layered model and all files at one depth, coh_pass emits one Unresolved COH003 per file whose callees are unplaced (including external callees such as console.log). Decide whether external callees should be excluded or the Unresolved collapsed to one repo-level note.
