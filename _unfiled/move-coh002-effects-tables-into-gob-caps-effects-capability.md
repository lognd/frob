+++
id = "01M5M05N51MZ3RYXFYJT28A73Q"
title = "Move COH002 effects tables into gob-caps Effects capability"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-23T09:06:18Z"
updated = "2026-10-23T09:06:18Z"
scope = ["crates/gob-caps/**"]
+++

Found while working ~T0TGDAS: the COH002 effects tables live in crates/grimble-check/src/effects.rs; the gob-caps Capability::Effects column is a gap for Rust, Python, C# and TypeScript. Move the tables into the language adapters.
