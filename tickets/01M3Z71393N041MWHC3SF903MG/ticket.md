+++
id = "01M3Z71393N041MWHC3SF903MG"
title = "gob-directives: [directives] namespaces as a ConfigTable and milestone-2 claim verbs"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T23:11:08Z"
idempotency_key = "m2-dirconf"
labels = ["milestone:2"]
scope = ["crates/gob-directives/**", "crates/gob-macros/**", "docs/reference/**"]

[[acceptance]]
text = "Given a frob:effects reads(X) writes(Y) directive, when scanned, then the record carries the parsed atom set and the directive page documents it"
bound = false
+++

code-model.md 4 after D63: honoured namespaces come from a materialized [directives] table; add the claim directives frob:effects (vocabulary of neatness.md 3), frob:pure, frob:honest, frob:core, frob:shell, frob:hook, frob:dispatcher, frob:idempotent, frob:trusted and frob:calls as parsed records with schema and docs; no evaluation yet.
