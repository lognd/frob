+++
id = "01M7EXTEHZXMP4D8DWMK0RBZN2"
title = "crunk content: description and placeholders on [[key]]"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:25Z"
updated = "2026-11-15T06:20:25Z"
idempotency_key = "crunkplan-2401425d7c54"
labels = ["no-story"]

[[acceptance]]
text = "a string missing a declared placeholder raises a finding"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M8.
Evidence: keys have no description or placeholder metadata
Remedy: add fields and validate placeholder use
Crates/files: crates/crunk-spec content
Verify against HEAD first; the audit ran on a stale binary.
