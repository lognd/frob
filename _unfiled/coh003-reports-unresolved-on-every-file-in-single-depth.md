+++
id = "01M5M34XTDZEZ08TAA78872RRP"
title = "COH003 reports Unresolved on every file in single-depth repos with no layered model"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T09:58:20Z"
updated = "2026-10-23T09:58:20Z"
scope = ["crates/grimble-check/**"]
+++

Found while working 62Y1A18: with no layered model and all files at one depth, coh_pass emits one Unresolved COH003 per file whose callees are unplaced (including external callees such as console.log). Decide whether external callees should be excluded or the Unresolved collapsed to one repo-level note.
