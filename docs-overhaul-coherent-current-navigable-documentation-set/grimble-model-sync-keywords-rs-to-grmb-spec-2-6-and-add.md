+++
id = "01M6BYJWDYKT5B9DCXFA1W814E"
title = "grimble-model: sync keywords.rs to grmb-spec 2.6 and add MDL031 pack-kind/membership rule"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T16:20:21Z"
updated = "2026-11-01T17:56:18Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/keywords.rs", "crates/grimble-model/src/check.rs", "crates/grimble-model/tests/corpus/**", "crates/grimble-model/tests/corpus.rs", "docs/reference/rules/MDL031.md", "crates/grimble-model/src/rules/mdl031.md", "crates/grimble-model/tests/keywords.rs"]

[[acceptance]]
text = "Given keywords.rs, when compared with the grmb-spec.md 2.6 table, then it equals it (adds attests, for, use, chain, the rev 2 planning words; drops title) and a pack kind equal to a planning word is refused with MDL031 (parent AC2)"
bound = true

[[acceptance]]
text = "Given MDL031, when a pack kind equals a table word, then it is refused; crates/grimble-model/tests/corpus/plan is respelled. Mockup loading and the D157 membership review move to ~ZP5KR2Q"
bound = true
+++

Child of ~03B2YRN. Carries parent AC2 and AC3. Do first: the parser children use the keyword table.
