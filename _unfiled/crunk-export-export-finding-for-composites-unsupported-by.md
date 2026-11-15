+++
id = "01M7EXS8WBSAPWGMM636P5M6PK"
title = "crunk export: EXPORT finding for composites unsupported by uss, csharp, figma"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK8FEAC1T9J0XMDFWKG0Y"
reporter = "lognd"
created = "2026-11-15T06:19:46Z"
updated = "2026-11-15T06:19:46Z"
idempotency_key = "crunkplan-aa005d4c56f9"
labels = ["no-story"]

[[acceptance]]
text = "exporting a composite to uss yields a finding naming token and target"
bound = false

[[acceptance]]
text = "no finding for supported (target, composite) pairs"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H3.
Evidence: unsupported composites are silently omitted per target
Remedy: one EXPORT finding per (target, composite) that cannot be represented
Crates/files: crates/crunk-export, crates/crunk-rules export rules
Verify against HEAD first; the audit ran on a stale binary.
