+++
id = "01M7EXTFJ3MH40YDCSNZNB22WE"
title = "crunk schema: JSON schemas for component, screen, flow, content, tokens and voice files"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:26Z"
updated = "2026-11-15T06:20:26Z"
idempotency_key = "crunkplan-f0a553a2fa2f"
labels = ["no-story"]

[[acceptance]]
text = "crunk schema --kind screen prints a valid JSON schema"
bound = false

[[acceptance]]
text = "fixture files validate against their schema"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M11.
Evidence: no schemas for authoring files
Remedy: ship JSON schemas and a crunk schema --kind verb
Crates/files: crates/crunk, crates/crunk-spec
Verify against HEAD first; the audit ran on a stale binary.
