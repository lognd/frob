+++
id = "01M642304NQ5XQP3WWD0T8Z2BM"
title = "CAP: capability use reached through a call into another node is not attributed"
type = "task"
category = "todo"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-30T05:59:17Z"
idempotency_key = "vnvd3q1-cross-node"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "docs/design/output-atoms.md"]

[[acceptance]]
text = "a call that resolves to a function in another node propagates that function's capability uses to the caller's node, or reports Unresolved"
bound = false
+++

Case q07. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
