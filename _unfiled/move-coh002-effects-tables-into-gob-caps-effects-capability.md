+++
id = "01M5M05N51MZ3RYXFYJT28A73Q"
title = "Move COH002 effects tables into gob-caps Effects capability"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T09:06:18Z"
updated = "2026-11-14T11:31:14Z"
labels = ["no-story"]
scope = ["crates/gob-caps/**", "crates/grimble-check/**", "crates/gob-ir/**", "docs/design/grimble/rule-families.md", "docs/**", "crates/gob-check/src/applicability.rs"]

[[acceptance]]
text = "COH002 effects tables live in gob-caps (Capability::Effects provided per language adapter) and grimble-check reads them from there; effects.rs holds no per-language tables"
bound = true
+++

Found while working ~T0TGDAS: the COH002 effects tables live in crates/grimble-check/src/effects.rs; the gob-caps Capability::Effects column is a gap for Rust, Python, C# and TypeScript. Move the tables into the language adapters.

no-story: internal engineering task in gob-caps; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
