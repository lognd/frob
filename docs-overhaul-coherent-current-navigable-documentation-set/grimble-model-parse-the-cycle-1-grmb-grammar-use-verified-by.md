+++
id = "01M69AHE03R04HDKKDT03B2YRN"
title = "grimble-model: parse the cycle 1 grmb grammar (use, verified_by, => arms, : outcomes, list chains, system membership)"
type = "task"
category = "todo"
priority = "high"
points = 8
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T15:51:33Z"
updated = "2026-10-31T16:38:21Z"
idempotency_key = "grmb-cycle1-parser"
scope = ["crates/grimble-model/**", "docs/reference/rules/**"]

[[acceptance]]
text = "The parser accepts every cycle 1 spelling of grmb-spec.md (use, verified_by on every entity incl. manual, step : outcome with idempotent/open, arm =>, retry [S] max N [within T], list waypoint chains with => outcome maps, on page, actor in node, r# escape, sorry whole body) and reports each pre-cycle-1 spelling as MDL012 with the replacement"
bound = false

[[acceptance]]
text = "keywords.rs equals the grmb-spec.md 2.6 table (adds attests, for, use, chain, the rev 2 planning words; drops title) and refuses a pack kind equal to a planning word (MDL031)"
bound = false

[[acceptance]]
text = "MDL031 implements the D157 membership rule; crates/grimble-model/tests/corpus/plan is respelled and the notes/research/grmb-corpus mockups load with only their documented findings"
bound = false

[[acceptance]]
text = "Code comments citing grmb-planning sections cite grmb-spec.md sections (11-17)"
bound = false

[[acceptance]]
text = "The fold and the graph export use the D186 names: actor clause attr in_node (was node), impl attr and export edge on_page (was requires_page), export edge in_node (was actor_node), title lands in the Doc facet, review= produces attr until, goal dimension is attr:dimension in Attr; the one-time digest change is restamped by grimble ack with reason respelling (D186)"
bound = false
+++

Follow-up of ~MHGA5VN cycle 1: the spec was respelled (D150-D165) but the shipped P1 parser (crates/grimble-model, leased by ERF5VCQ at the time) still reads the rev 1 spellings.
