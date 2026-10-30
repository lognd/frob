+++
id = "01M6422ZRSX74XT6RD0BG4T2RC"
title = "CAP: Python receiver types from constructor calls (socket) are not tracked"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-30T05:02:34Z"
idempotency_key = "vnvd3q1-py-recv"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "docs/design/output-atoms.md", "docs/design/binding.md"]

[[acceptance]]
text = "a value built by a capability constructor keeps its type through assignment so connect and send are reported"
bound = true
+++

Cases p12 p13. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
