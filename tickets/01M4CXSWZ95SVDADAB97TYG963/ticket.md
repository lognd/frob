+++
id = "01M4CXSWZ95SVDADAB97TYG963"
title = "Python type facts from ty or pyright as a bound tool, with [types] trust = checked | annotated | none"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:33Z"
updated = "2026-10-08T04:54:33Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/gob-check/**", "crates/gob-exec/**"]

[[acceptance]]
text = "Given a file that ty checks clean, when resolved, then annotated call targets are Must; given a failing check, then they are claimed (May)"
bound = false
+++

docs/design/cohesion.md 2.2. hullbreach platform has ty.toml. Annotations count as exact only when the checker ran clean in strict mode on that file; ignore comments demote their line.
