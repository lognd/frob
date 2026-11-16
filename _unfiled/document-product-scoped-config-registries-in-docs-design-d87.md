+++
id = "01M64A0B2ZN3RQNY73KMTGYAND"
title = "Document product-scoped config registries in docs/design (D87)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T17:06:00Z"
updated = "2026-11-16T18:42:49Z"
scope = ["docs/design/**"]

[[acceptance]]
text = "Given docs/design, when a reader looks up gob-config registries, then the design docs describe product scoping (crates/gob-config/src/product.rs) and dynamic-key tables under D87."
bound = true
+++

Found while working ~394FZ5T: gob-config registries are now product-scoped (see crates/gob-config/src/product.rs). docs/design was outside that lease; read D87 and document product scoping and dynamic-key tables there.
