+++
id = "01M666NX8TN1R3X13Q4S9CTJ1V"
title = "CAP: parse 'provides C via S' and treat S as a capability boundary in transitive summaries"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-30T10:46:22Z"
updated = "2026-10-30T22:20:37Z"
scope = ["crates/grimble-model/src/**", "crates/grimble-bind/src/caps.rs", "docs/design/grimble-capabilities-v3.md", "crates/grimble-bind/src/model.rs", "crates/grimble-bind/tests/**", "crates/grimble-model/tests/**"]

[[acceptance]]
text = "'provides C via S' parses in grimble-model and propagate_cross_node stops at the provider boundary"
bound = true
+++

Found while working 6ZD117V: grimble-capabilities-v3.md 5.3 provides/via is not parsed by grimble-model, so no wrapper can be declared a boundary. Needs parser, model, and propagate_cross_node stopping at a provider.
