+++
id = "01M7EXTDXS5MP5AWSEBF8CXR6Q"
title = "crunk A11Y: T0/T1 rules for heading order, landmarks and accessible names"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:20:24Z"
updated = "2026-11-15T06:20:24Z"
idempotency_key = "crunkplan-709eaea88440"
labels = ["no-story"]

[[acceptance]]
text = "skipped heading level raises a finding"
bound = false

[[acceptance]]
text = "missing landmark raises a finding"
bound = false

[[acceptance]]
text = "unnamed button raises a finding"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M4.
Evidence: no T0/T1 A11Y rules exist
Remedy: add A11Y rules over ingested html/scenes
Crates/files: crates/crunk-rules a11y
Verify against HEAD first; the audit ran on a stale binary.
