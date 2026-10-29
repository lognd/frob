+++
id = "01M64A0B2ZN3RQNY73KMTGYAND"
title = "Document product-scoped config registries in docs/design (D87)"
type = "docs"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T17:06:00Z"
updated = "2026-10-29T17:06:00Z"
scope = ["docs/design/**"]
+++

Found while working ~394FZ5T: gob-config registries are now product-scoped (see crates/gob-config/src/product.rs). docs/design was outside that lease; read D87 and document product scoping and dynamic-key tables there.
