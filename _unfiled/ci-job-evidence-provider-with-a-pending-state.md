+++
id = "01M7EXQXVGH1K278D3HX33ET2X"
title = "ci-job evidence provider with a pending state"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:19:02Z"
updated = "2026-11-15T06:19:03Z"
labels = ["no-story"]

[[acceptance]]
text = "A running job yields Pending, a passed job Pass (test)"
bound = false
+++

Source: frob-audit-meta.md M13. Evidence: no provider reads a CI job as evidence. Remedy: add provider returning Pending until the job completes. Files: crates/frob-evidence/**.
