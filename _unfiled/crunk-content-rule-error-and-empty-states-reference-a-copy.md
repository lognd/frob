+++
id = "01M7EXTES3W5K5EJTHGTB35PZ0"
title = "crunk CONTENT rule: error and empty states reference a copy key"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:25Z"
updated = "2026-11-15T06:20:25Z"
idempotency_key = "crunkplan-f66737cc01f4"
labels = ["no-story"]

[[acceptance]]
text = "literal text in an error state raises a finding"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M8.
Evidence: error/empty states may hold literal text
Remedy: rule requires a copy key reference
Crates/files: crates/crunk-rules content
Verify against HEAD first; the audit ran on a stale binary.
