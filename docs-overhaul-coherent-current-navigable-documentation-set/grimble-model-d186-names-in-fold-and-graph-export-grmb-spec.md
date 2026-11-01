+++
id = "01M6BYKA5HDJT3KSKGQ2QQ6V9H"
title = "grimble-model: D186 names in fold and graph export, grmb-spec section citations, digest restamp"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T16:20:35Z"
updated = "2026-11-01T20:15:38Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/fold.rs", "crates/grimble-model/src/fold/**", "crates/grimble-model/src/plan.rs", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/src/plan_index.rs", "crates/grimble-model/src/dump.rs", "crates/grimble-model/src/model.rs", "crates/grimble-model/src/fmt/plan.rs", "crates/grimble-model/src/rules/mdl028.md", "crates/grimble-model/tests/planning.rs", "crates/grimble-model/tests/corpus/plan/**", "crates/gob-check/src/sibling_doc.rs", "docs/schemas/sibling.json", "crates/grimble-model/tests/corpus/u/encoding/assumed/**", "docs/reference/rules/MDL028.md"]

[[links]]
kind = "blocked-by"
target = "01M6BYJWDYKT5B9DCXFA1W814E"

[[acceptance]]
text = "Given code comments in grimble-model citing grmb-planning sections, when reviewed, then they cite grmb-spec.md sections (11-17) (parent AC4)"
bound = true

[[acceptance]]
text = "Given the fold and the graph export, when run, then they use the D186 names: actor clause attr in_node (was node), impl attr and export edge on_page (was requires_page), export edge in_node (was actor_node), title lands in the Doc facet, review= produces attr until, goal dimension is attr:dimension in Attr (digest restamp deferred: no tracked grimble.lock carries planning digests)"
bound = false
+++

Child of ~03B2YRN. Carries parent AC4 and AC5. Independent of the parser children except for shared crate; blocked-by the keyword child only to serialize crate-wide comment edits.
