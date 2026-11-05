+++
id = "01M6PDM6HRSQJENR0VHT5YNDRZ"
title = "COH002 effect_methods and trivial tables, plus sqlite3/axios/localStorage atoms, into the registry"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-05T17:55:37Z"
updated = "2026-11-05T18:23:06Z"
labels = ["no-story", "no-story: internal engineering follow-up of P8A3N49; no user-visible outcome of its own"]
scope = ["crates/grimble-check/src/effects.rs", "packs/core-effects/atoms.toml", "crates/grimble-bind/tests/caps.rs", "docs/design/grimble/rule-families.md"]

[[acceptance]]
text = "COH002 reads methods and trivial names from gob_ir::registry"
bound = true
+++

Found while working P8A3N49: COMMON_METHODS and the per-language trivial (logging) tables remain code constants in grimble-check; python sqlite3 and TS axios/localStorage qualifiers were in the old tables but are not registry atoms. Move them into the registry (overlaps T28A73Q).
