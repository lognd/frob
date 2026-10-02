+++
id = "01M3Z712SX9DEEAF4K8ER867TX"
title = "G04: data packs and registry drift-lock specification"
type = "docs"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T22:03:52Z"
idempotency_key = "m2-packs"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712KRPYF3DQG6ZFCWVPS7"

[[acceptance]]
text = "Given the specification, when a pack adds an atom with a detector for one language, then the matrix shows unknown for other languages and not-applicable only where the pack declares it"
bound = false
+++

grimble-model.md sections 5 and 9.6: pack format (atoms, detectors per language with detector kind, callee vocabularies, claims), the registry as inventory entries in a shared gob crate, the drift-lock that pins pack versions per repository, materialized knobs, and the not-applicable cell declaration.
