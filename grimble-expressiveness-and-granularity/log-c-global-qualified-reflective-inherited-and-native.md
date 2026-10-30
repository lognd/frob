+++
id = "01M64230Q2FSG2WXTFT4ENDA4R"
title = "LOG: C# global-qualified, reflective, inherited and native-interop output forms are not resolved"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-30T03:34:17Z"
idempotency_key = "vnvd3q1-log-cs"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/grimble-bind/**", "docs/design/output-atoms.md"]

[[acceptance]]
text = "global:: qualified names, reflection, inherited helpers and DllImport output functions are resolved or reported Unresolved"
bound = true
+++

Cases cs03 cs04 cs06 cs07. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
