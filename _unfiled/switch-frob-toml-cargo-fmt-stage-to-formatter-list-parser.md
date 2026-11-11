+++
id = "01M5HWMZ5CEY7CETNK4NDSKWGM"
title = "Switch frob.toml cargo fmt stage to formatter-list parser"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T13:26:16Z"
updated = "2026-11-11T05:12:12Z"
labels = ["no-story"]
scope = ["frob.toml"]

[[acceptance]]
text = 'frob.toml cargo fmt stage sets parser = "formatter-list" so unformatted files surface as FMT001 findings'
bound = true
+++

found while working ~H36992B

no-story: internal engineering task in frob.toml; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
