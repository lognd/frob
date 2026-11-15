+++
id = "01M7EXS8CAJ2DJ3168W20HD3JN"
title = "crunk export: emit composite tokens in css and tailwind targets"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M7ETK8FEAC1T9J0XMDFWKG0Y"
reporter = "lognd"
created = "2026-11-15T06:19:46Z"
updated = "2026-11-15T06:19:46Z"
idempotency_key = "crunkplan-a79a77e8868f"
labels = ["no-story"]

[[acceptance]]
text = "a project with a shadow and a typography composite exports both in css and tailwind (snapshot test)"
bound = false

[[acceptance]]
text = "round trip: exported css parses with crunk-ingest"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H3.
Evidence: composite tokens (shadow, typography, border) are dropped from css/tailwind exports
Remedy: emit composites as css custom properties / tailwind theme keys
Crates/files: crates/crunk-export (css, tailwind)
Verify against HEAD first; the audit ran on a stale binary.
