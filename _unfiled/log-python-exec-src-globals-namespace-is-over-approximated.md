+++
id = "01M65FKMHQNSJ9X0DW4MF6QV0F"
title = "LOG: Python exec(src, globals) namespace is over-approximated by the caller scope"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-03T05:56:44Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/output-atoms.md"]
+++

found while working 01M64230T88F77RTBYS9M3CY3C: the explicit globals mapping is ignored.
