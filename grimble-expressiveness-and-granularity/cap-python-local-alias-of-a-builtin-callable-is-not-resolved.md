+++
id = "01M6422ZCGB47DJWWY78B9HSHH"
title = "CAP: Python local alias of a builtin callable is not resolved"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-30T01:34:10Z"
idempotency_key = "vnvd3q1-py-alias"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**"]

[[acceptance]]
text = "assignment aliases of builtins and module attributes resolve to the origin symbol"
bound = false
+++

Case p03: alias of open not resolved. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
