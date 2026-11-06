+++
id = "01M4P0SXRPC9QT51PXGV9ZJ9AA"
title = "dup ratchet: tighten T1 and T2 from warn to error and shrink the baseline"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-11-06T07:38:39Z"
scope = ["crates/gob-rules/src/registry.rs", "frob-baseline.toml", "docs/design/dup.md", "changelog.d/01M4P0SXRPC9QT51PXGV9ZJ9AA.changed.md"]

[[acceptance]]
text = "T1 and T2 severity is error by default after a one-cycle warn burn-in"
bound = true

[[acceptance]]
text = "Baseline entry count is lower than at T0 landing, or each remaining entry has a justifying ticket"
bound = true

[[acceptance]]
text = "Docs and generated rule pages updated"
bound = true
+++
