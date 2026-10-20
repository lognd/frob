+++
id = "01M3Z712PSRGMHPGJ01CMBK6TR"
title = "G03: sibling JSON contract and schema"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:52:21Z"
idempotency_key = "m2-sibling"
labels = ["milestone:2"]
scope = ["docs/design/**", "docs/schemas/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712KRPYF3DQG6ZFCWVPS7"

[[acceptance]]
text = "Given the schema, when a sample grimble output and a sample crunk output are validated, then both pass and a document with a missing required mark fails"
bound = true
+++

grimble-model.md 9.5: specify docs/schemas/sibling.json (schema_version, product, fidelity per language, findings with rule, severity incl. Unresolved reasons, polarity, subjects_examined, required mark, exception with opaque ticket, suppressed list, entities and bindings), the compute digest frob checks, version negotiation and refusal, and the frob behaviour for a configured-but-absent sibling.
