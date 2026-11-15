+++
id = "01M7EXTDGGKQWTVE5VCAZJ2KT0"
title = "crunk components: [[transitions]] table and tailwind transition keys"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:24Z"
updated = "2026-11-15T06:20:24Z"
idempotency_key = "crunkplan-bef296baf403"
labels = ["no-story"]

[[acceptance]]
text = "a component [[transitions]] entry parses and is judged by MOTION rules"
bound = false

[[acceptance]]
text = "tailwind transition-colors resolves to a duration token"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M3.
Evidence: components cannot declare transitions; tailwind transition keys unrecognised
Remedy: add [[transitions]] to component schema and map tailwind transition-* keys
Crates/files: crates/crunk-spec, crates/crunk-tailwind
Verify against HEAD first; the audit ran on a stale binary.
