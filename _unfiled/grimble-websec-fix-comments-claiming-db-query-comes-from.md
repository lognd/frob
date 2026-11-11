+++
id = "01M6KN33275NHTQFQ9JC5P7YJN"
title = "grimble websec: fix comments claiming db.query comes from core-effects"
type = "docs"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-04T16:08:21Z"
updated = "2026-11-11T02:43:44Z"
idempotency_key = "followup-websec-dbquery-comments"
scope = ["packs/grimble-websec/pack.toml", "crates/grimble-check/src/websec_pack.rs", "changelog.d/**"]

[[acceptance]]
text = "pack.toml and websec_pack.rs no longer claim db.query comes from core-effects"
bound = true
+++

db.query is not a registered atom (may db.query raises MDL016). pack.toml line 3 and websec_pack.rs module doc still say it comes from core-effects. Found while landing WJH6HZ7.
