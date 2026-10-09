+++
id = "01M4FCET3GBDKBRK9JP83H49E3"
title = "grmb planning layer design: actors, goal variant trees, scenarios with Zig/Rust outcome handling, impl blocks bound to code, ticket lifecycle (D123+)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T03:49:07Z"
updated = "2026-10-09T06:22:09Z"
labels = ["grimble", "creates:docs/design/grmb-planning.md"]
scope = ["changelog.d/**", "docs/design/grmb-spec.md", "docs/design/grimble-model.md", "docs/design/grmb-planning.md", "docs/design/README.md"]

[[acceptance]]
text = "Given the owner mockup and the coordinator brief, when docs/design/grmb-planning.md lands, then it specifies the grammar (EBNF), operators, well-formedness rules with ids, U encoding, graph JSON status and obligations, the frob ticket join and the milestone cut, and docs/design/README.md records D123 onward"
bound = true

[[acceptance]]
text = "Given the milestone cut, when the design lands, then an epic with sized P1-P6 child tickets exists in the ledger"
bound = true
+++

Owner 2026-10-08 mockup: a planning grammar mirroring the design cycle (more specific per level), bound to code and tickets, and to code when tickets complete; UML concepts with Zig/Rust-like variant handling. The coordinator brief with decisions is given to the implementer.
