+++
id = "01M7EXTC7M0K9XQTRF67TFNH0Q"
title = "crunk: validate component instances against props and variants"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:23Z"
updated = "2026-11-15T06:20:23Z"
idempotency_key = "crunkplan-224dde7c3d67"
labels = ["no-story"]

[[acceptance]]
text = "an undeclared variant on an instance raises a finding"
bound = false

[[acceptance]]
text = "a declared one passes"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M2.
Evidence: instances can name props/variants the component does not declare
Remedy: validate instance attributes against the component file
Crates/files: crates/crunk-spec, crates/crunk-rules component rules
Verify against HEAD first; the audit ran on a stale binary.
