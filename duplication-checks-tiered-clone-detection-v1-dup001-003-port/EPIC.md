+++
id = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
title = "Duplication checks: tiered clone detection (v1 DUP001-003 port)"
type = "epic"
category = "todo"
priority = "medium"
points = 13
reporter = "lognd"
created = "2026-10-11T17:40:03Z"
updated = "2026-10-11T17:40:03Z"
+++

Port and extend the v1 duplication check. Tiers: T0 token-window clone of the diff in frob check; T1 structural clones on land; T2 whole-repo near-miss in CI/nightly with ratchet baseline. Speed first: diff-scoped, content-addressed, cached. Error by default, not opt-in. Motivation: weaker agents reimplement existing helpers. v1 notes: notes/v1/gates-and-rules.md, graph-lang-dsl.md. Target 0.534.
