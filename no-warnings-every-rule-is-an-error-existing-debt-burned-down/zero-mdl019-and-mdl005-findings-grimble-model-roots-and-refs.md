+++
id = "01M627BCZMXG78QDBA465PZ5J2"
title = "Zero MDL019 and MDL005 findings (grimble model roots and refs)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-28T21:41:08Z"
updated = "2026-10-28T23:47:43Z"
idempotency_key = "b755-mdl"
scope = ["design/model.grmb", "grimble.toml"]

[[acceptance]]
text = "frob check reports zero MDL019 and MDL005 findings"
bound = true
+++

Split from ~B755NCR (mis-scoped to docs/design/docs.md). MDL019: grimble-model resources/inline grmb files reachable from no root (frob.toml exclude or models). MDL005: design/model.grmb lines 99,106 point at missing crates/frob/tests/remedies.rs and web_conformance.rs.
