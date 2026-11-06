+++
id = "01M6R956D5SKEVNBREQM8X95K5"
title = "grimble vet refresh verb wires advisory refresh"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-06T11:16:00Z"
updated = "2026-11-06T11:51:14Z"
labels = ["no-story"]
scope = ["crates/gob-dev/profile.toml", "crates/grimble/src/lib.rs", "crates/grimble/src/vet_refresh.rs", "docs/design/shared/charter.md", "docs/reference/cli/grimble.md"]
+++

grimble_vet::refresh exists (WQ6SCFF) but no CLI verb calls it. Add 'grimble vet refresh <advisory-db-checkout>', a staleness check against SNAPSHOT.toml as_of, docs, gen all, profile.toml scenario, verbs.rs entry.
