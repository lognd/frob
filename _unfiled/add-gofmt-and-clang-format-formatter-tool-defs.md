+++
id = "01M5HWMZ2BWEFGHEA08KSSQVNQ"
title = "Add gofmt and clang-format formatter tool defs"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T13:26:16Z"
updated = "2026-11-14T10:30:26Z"
labels = ["no-story"]
scope = ["crates/gob-check/**", "docs/reference/tool-stages.md"]

[[acceptance]]
text = "gofmt and clang-format std tool defs parse, carry unattended fixes, and clang-format diagnostics parse to FMT001 files"
bound = true
+++

found while working ~H36992B; gofmt has no --version

no-story: internal engineering task in gob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
