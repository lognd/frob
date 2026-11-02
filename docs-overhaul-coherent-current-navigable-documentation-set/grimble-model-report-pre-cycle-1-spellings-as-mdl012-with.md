+++
id = "01M6BYKA22XMCHVENG2V82CNAR"
title = "grimble-model: report pre-cycle-1 spellings as MDL012 with the replacement"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T16:20:34Z"
updated = "2026-11-02T05:23:19Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/check.rs", "crates/grimble-model/src/parse/**", "crates/grimble-model/tests/inline.rs", "docs/reference/rules/MDL012.md", "crates/grimble-model/src/parse.rs", "crates/grimble-model/src/fmt.rs", "crates/grimble-model/src/fmt/**", "crates/grimble-model/src/plan_index.rs", "crates/grimble-model/src/rules/mdl012.md", "crates/grimble-model/tests/corpus/**", "crates/grimble-model/tests/cycle1_decls.rs", "crates/grimble-model/tests/model.rs", "docs/reference/rules/README.md", "x", "crates/grimble-check/tests/**", "crates/grimble/tests/**", "crates/grimble/src/**", "crates/grimble-bind/src/rules/**", "crates/grimble-bind/tests/**", "docs/reference/rules/**"]

[[links]]
kind = "blocked-by"
target = "01M6BYK3QNNF0WHQW2Y0Q2TMVM"

[[acceptance]]
text = "Given a source using any pre-cycle-1 spelling, when parsed or checked, then each is reported as MDL012 naming the replacement (part of parent AC1)"
bound = false
+++

Child of ~03B2YRN. Final part of parent AC1.
