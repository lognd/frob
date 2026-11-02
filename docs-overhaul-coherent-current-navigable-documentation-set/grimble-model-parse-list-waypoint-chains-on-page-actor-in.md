+++
id = "01M6BYK3QNNF0WHQW2Y0Q2TMVM"
title = "grimble-model: parse list waypoint chains, on page, actor in node, r# escape, sorry whole body"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T16:20:28Z"
updated = "2026-11-02T03:57:55Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/parse/**", "crates/grimble-model/src/lex.rs", "crates/grimble-model/src/ast.rs"]

[[links]]
kind = "blocked-by"
target = "01M6BYK3M8ZM6K3P9V3M7Y61ZQ"

[[acceptance]]
text = "Given grmb-spec.md cycle 1 source, when parsed, then list waypoint chains with => outcome maps, on page, actor in node, the r# escape and a sorry whole body are accepted (part of parent AC1)"
bound = false
+++

Child of ~03B2YRN. Part 2 of parent AC1. Shares parse.rs with the previous sibling, hence blocked-by.
