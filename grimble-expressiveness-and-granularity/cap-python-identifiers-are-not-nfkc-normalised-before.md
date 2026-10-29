+++
id = "01M6422ZYR690QV4JF17VYCFGM"
title = "CAP: Python identifiers are not NFKC-normalised before resolution"
type = "task"
category = "todo"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T14:47:39Z"
idempotency_key = "vnvd3q1-py-nfkc"
scope = ["crates/grimble-check/**,crates/gob-symbols/**,crates/gob-caps/**,crates/gob-languages/**"]

[[acceptance]]
text = "identifiers resolve after NFKC normalisation as the interpreter does, for capability and LOG detectors"
bound = false
+++

Case p27 and LOG case py12. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
