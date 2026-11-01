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
updated = "2026-11-01T17:38:16Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/keywords.rs", "crates/grimble-model/src/check.rs", "crates/grimble-model/tests/corpus/**", "crates/grimble-model/tests/corpus.rs", "docs/reference/rules/MDL031.md"]

[[acceptance]]
text = "Given keywords.rs, when compared with the grmb-spec.md 2.6 table, then it equals it (adds attests, for, use, chain, the rev 2 planning words; drops title) and a pack kind equal to a planning word is refused with MDL031 (parent AC2)"
bound = false

[[acceptance]]
text = "Given MDL031, when it runs, then it implements the D157 membership rule; crates/grimble-model/tests/corpus/plan is respelled and the notes/research/grmb-corpus mockups load with only their documented findings (parent AC3)"
bound = false
+++

Child of ~03B2YRN. Carries parent AC2 and AC3. Do first: the parser children use the keyword table.
