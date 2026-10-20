+++
id = "01M4CXSWZ95SVDADAB97TYG963"
title = "Python type facts from ty or pyright as a bound tool, with [types] trust = checked | annotated | none"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:33Z"
updated = "2026-10-14T12:27:15Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/gob-check/**", "crates/gob-exec/**", "crates/frob/**", "docs/reference/**", "docs/schemas/**"]

[[acceptance]]
text = "Given a file that ty checks clean, when resolved, then annotated call targets are Must; given a failing check, then they are claimed (May)"
bound = true
+++

docs/design/cohesion.md 2.2. hullbreach platform has ty.toml. Annotations count as exact only when the checker ran clean in strict mode on that file; ignore comments demote their line.
