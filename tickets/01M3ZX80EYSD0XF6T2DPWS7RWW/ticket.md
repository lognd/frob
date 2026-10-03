+++
id = "01M3ZX80EYSD0XF6T2DPWS7RWW"
title = "Reserved pack names, config_tables namespace and provenance prefixes"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-pack-names"
labels = ["milestone:2", "area:security", "good-first"]
scope = ["crates/gob-packs/src/names.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FG2JNTHKVQ5R535DAVZ"

[[acceptance]]
text = "Given a repository pack named grimble-extras, when loaded, then PACK005 names the reserved prefix"
bound = false

[[acceptance]]
text = "Given a pack declaring config table [grimble.x], when loaded, then PACK005 is returned and only [packs.NAME] is accepted"
bound = false
+++

Implements security.md section 2.8 (SEC-30, SEC-32).

Names starting with std, grimble, frob, crunk, core or gob are reserved for built-in packs (PACK005 elsewhere); a pack's config_tables may declare only [packs.NAME]; provenance is shown with builtin:, repo:packs/NAME or ext:HOST/NAME.
