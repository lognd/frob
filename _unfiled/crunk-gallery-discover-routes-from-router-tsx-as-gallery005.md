+++
id = "01M4YZCC0PBYFW8CSBB8ERKFXE"
title = "crunk-gallery: discover routes from router.tsx as GALLERY005 input"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-15T05:08:26Z"
updated = "2026-11-09T03:16:10Z"
scope = ["crates/crunk-gallery/**", "crates/crunk/src/gallery.rs", "crates/crunk/tests/gallery.rs", "changelog.d/01M5ERKFXE0000000000000001.added.md", "docs/reference/cli/crunk.md", "changelog.d/01M4YZCC0PBYFW8CSBB8ERKFXE.added.md"]

[[acceptance]]
text = "router.tsx route objects and JSX Route elements parse to absolute paths with nesting, dynamic segments kept verbatim"
bound = true

[[acceptance]]
text = "Unsupported path shapes (identifier, interpolated template) and route-less sources return a typed RouterError, never a panic"
bound = true

[[acceptance]]
text = "crunk gallery check --router feeds the discovered routes to GALLERY005 and --route still works; an unreadable or unsupported router is refused with E-GALLERY-ROUTER"
bound = true
+++

GALLERY005 currently takes routes via repeatable --route; derive them from the app router. Found while working ~AKETJJH.
