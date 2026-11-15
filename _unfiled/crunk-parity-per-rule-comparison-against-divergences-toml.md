+++
id = "01M7EXQVR9F57BP8WF58TH8ABT"
title = "crunk parity: per-rule comparison against divergences.toml"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:00Z"
updated = "2026-11-15T06:19:00Z"
labels = ["no-story"]

[[acceptance]]
text = "Unlisted per-rule divergence fails the parity test"
bound = false
+++

Source: frob-audit-meta.md M8. Evidence: tests/crunk-parity/divergences.toml is compared only in aggregate. Remedy: compare per rule. Files: tests/crunk-parity/**.
