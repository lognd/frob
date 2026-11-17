+++
id = "01M65FKMDW5CXZ40878K73M31T"
title = "LOG: Python star import from external modules is silently unresolved"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-17T06:43:53Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md", "crates/grimble-check/tests/**"]

[[acceptance]]
text = "A bare builtin output call (print) after a Python star import of an external or unknown module is reported Unresolved, not a hit or silently clean"
bound = false
+++

found while working 01M64230T88F77RTBYS9M3CY3C: only project modules are expanded.
