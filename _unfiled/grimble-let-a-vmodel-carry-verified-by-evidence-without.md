+++
id = "01M7ET17BM017983KQXF9ZNSC3"
title = "grimble: let a vmodel carry verified_by evidence without MDL000/MDL012"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T05:14:12Z"
updated = "2026-11-15T06:46:57Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/check.rs", "crates/grimble-model/src/text.rs", "crates/grimble-model/tests/it/main.rs", "crates/grimble-model/tests/it/vmodel_verified_by.rs", "docs/design/grimble/grmb-spec.md"]

[[acceptance]]
text = "A vmodel accepts verified_by SEL; without MDL000 or MDL012"
bound = true

[[acceptance]]
text = "A vmodel accepts verified_by manual because=...; without MDL000 or MDL012"
bound = true

[[acceptance]]
text = "MDL000 prints verified_by as written, not the internal evidence name"
bound = true

[[acceptance]]
text = "grimble fmt keeps verified_by after ref on a vmodel"
bound = true
+++

Audit2 H1. See ~/projects/frob-audit2-grimble.md section H1 for evidence and remedy.
