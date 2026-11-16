+++
id = "01M648G0HAPTHCHX4BKCFHG5QT"
title = "CAP: TS static import default/namespace direct calls not emitted by path_uses"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T16:39:37Z"
updated = "2026-11-16T18:03:59Z"
scope = ["crates/gob-symbols/src/lookups.rs"]

[[acceptance]]
text = 'Given a TypeScript file with import cp from "x"; cp.exec(), when path_uses runs, then it emits a path use for x.exec'
bound = true
+++

found while working ~6CV37RW: import cp from 'x'; cp.exec() is not emitted as a path use.
