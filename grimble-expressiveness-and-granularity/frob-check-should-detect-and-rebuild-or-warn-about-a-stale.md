+++
id = "01M6BDWBY1XVHFBVCMK8P8875B"
title = "frob check should detect and rebuild or warn about a stale grimble sibling binary"
type = "bug"
category = "todo"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:28:26Z"
updated = "2026-11-01T11:28:26Z"
scope = ["crates/frob/src/**"]

[[acceptance]]
text = "frob check warns (or errors) when the resolved grimble sibling version or build id differs from frob"
bound = false
+++

A stale ~/.local/bin/grimble (0.532.0) on PATH produced misleading LOG001 results.
