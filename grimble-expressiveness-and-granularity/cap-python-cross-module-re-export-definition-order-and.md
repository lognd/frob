+++
id = "01M6422ZN7HKF98JDAP7XKRQQ2"
title = "CAP: Python cross-module re-export, definition-order and conditional binding are not resolved"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:38Z"
updated = "2026-10-30T04:35:25Z"
idempotency_key = "vnvd3q1-py-reexport"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "docs/design/output-atoms.md"]

[[acceptance]]
text = "a name imported under an alias in another project module, rebound after definition, bound in try/except, or conditionally shadowed resolves to every possible origin symbol"
bound = true
+++

Cases p09 p10 p26 p28. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
