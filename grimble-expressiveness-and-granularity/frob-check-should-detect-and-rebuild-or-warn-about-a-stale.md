+++
id = "01M6BDWBY1XVHFBVCMK8P8875B"
title = "frob check should detect and rebuild or warn about a stale grimble sibling binary"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:28:26Z"
updated = "2026-11-01T12:31:44Z"
scope = ["crates/frob/src/**", "crates/frob-check/src/sibling/mod.rs", "crates/frob-check/tests/it/sibling.rs", "changelog.d/01M6BDWBY1XVHFBVCMK8P8875B.fixed.md", "docs/design/sibling-contract.md"]

[[acceptance]]
text = "frob check warns (or errors) when the resolved grimble sibling version or build id differs from frob"
bound = true
+++

A stale ~/.local/bin/grimble (0.532.0) on PATH produced misleading LOG001 results.
