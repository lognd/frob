+++
id = "01M6422Z8JGE789ZHW4G68NRS1"
title = "CAP: Python wildcard import is not resolved to its module"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-30T00:25:11Z"
idempotency_key = "vnvd3q1-py-star"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "docs/design/grimble-capabilities-v3.md"]

[[acceptance]]
text = "from-import-star of a capability module resolves each bare name to its origin symbol and the use is reported"
bound = true
+++

Case p02: names bound by a wildcard import are not resolved. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
