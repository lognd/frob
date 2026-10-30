+++
id = "01M64230T88F77RTBYS9M3CY3C"
title = "LOG: Python project-module star import, long re-export chain and dynamic evaluation are not resolved"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:40Z"
updated = "2026-10-30T04:06:08Z"
idempotency_key = "vnvd3q1-log-py"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/grimble-bind/**", "docs/design/output-atoms.md"]

[[acceptance]]
text = "star imports from project modules, 4-step re-export chains and exec/eval of constant source resolve to the origin symbol"
bound = true
+++

Cases py07 py08 py09. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
