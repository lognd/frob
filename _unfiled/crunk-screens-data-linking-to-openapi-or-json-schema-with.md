+++
id = "01M7EXTE4X4YTC73EZE8BP68AG"
title = "crunk screens: [[data]] linking to OpenAPI or JSON Schema, with one rule"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:25Z"
updated = "2026-11-15T06:20:25Z"
idempotency_key = "crunkplan-26abbc169888"
labels = ["no-story"]

[[acceptance]]
text = "an unresolvable [[data]] link raises a finding"
bound = false

[[acceptance]]
text = "a valid one passes"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M7.
Evidence: screens cannot declare their data shape
Remedy: add [[data]] to screen files with a schema link and a rule that the link resolves
Crates/files: crates/crunk-spec, crates/crunk-rules
Verify against HEAD first; the audit ran on a stale binary.
