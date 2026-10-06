+++
id = "01M48Q4E637KNAGPTCZQKJ78C2"
title = "Measured fidelity and a capability-matrix snapshot for every adapter"
type = "story"
category = "todo"
priority = "high"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:41:00Z"
updated = "2026-10-06T13:41:00Z"
scope = ["crates/gob-symbols/**", "crates/gob-languages/**", "docs/reference/**"]

[[acceptance]]
text = "promoting an adapter's declared fidelity without corpus support fails"
bound = false

[[acceptance]]
text = "dropping a corpus operator case fails"
bound = false

[[acceptance]]
text = "every adapter has matrix, garbage and partial-parse cases"
bound = false
+++

testing.md 5: derive each adapter's fidelity from its conformance corpus (F1 units and containment, F2 Must lexical edges, F3 apply edges with status, F4 attrs, bound comments, regions, phases) and fail when declared differs from measured in either direction; snapshot every adapter's capability matrix; add an F0 case, a garbage-input case (no panic; Unresolved or NotApplicable) and a partial-parse case per adapter; generate doctor --languages and the languages page from the same data. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
