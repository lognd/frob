+++
id = "01M6422ZJ6EGH0AP4ZYT78E2WZ"
title = "CAP: Python dynamic code evaluation is not reported"
type = "task"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-29T21:13:19Z"
idempotency_key = "vnvd3q1-py-eval"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**"]

[[acceptance]]
text = "eval, exec and compile on a non-constant source yield an Unresolved finding naming the call"
bound = false
+++

Case p08. Constant sources should be parsed and resolved. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
