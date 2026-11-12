+++
id = "01M5HA927868ERRSB19JYF0QZE"
title = "GX focus: grid-axis groups and modal trap exemption"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:05:12Z"
updated = "2026-11-12T10:51:52Z"
labels = ["no-story"]
scope = ["crates/crunk-layout/**,crates/crunk-rules/src/rules/gx003.rs", "docs/reference/rules/GX003.md", "crates/crunk-rules/src/rules/gx003.md", "crates/crunk-rules/tests/it/gx_rules.rs", "crates/crunk-layout/**", "crates/crunk-rules/src/rules/gx003.rs"]

[[acceptance]]
text = "Given a focus group laid out on a grid, when GX003 runs, then neighbours are resolved along both axes, and a modal dialog that traps focus is exempt from the escape-route finding"
bound = true
+++

found while working Q2ZC9QM: modal dialogs legitimately trap focus; grid groups need 2D neighbours.

no-story: internal engineering task in crunk-layout; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
