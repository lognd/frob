+++
id = "01M642307T98S89GQ4APKW7X2J"
title = "CAP: no capability detection for TypeScript, JavaScript, Go, Java, C, C# and shell"
type = "task"
category = "in-progress"
priority = "critical"
points = 13
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T21:52:25Z"
idempotency_key = "vnvd3q1-nonpy"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "crates/gob-ir/**", "docs/design/universal-model.md", "docs/design/binding.md", "docs/reference/**"]

[[acceptance]]
text = "each supported language has registry entries for process, filesystem, network and environment capabilities, resolved through its import system, with tests"
bound = false
+++

Cases t01 t02 m02 g01 j01 cc01 c01 s01. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
