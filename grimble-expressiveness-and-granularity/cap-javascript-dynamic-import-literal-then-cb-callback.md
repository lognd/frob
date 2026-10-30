+++
id = "01M67HFSK2YWDBR37W8NTP5BXK"
title = "CAP: JavaScript dynamic import('literal').then(cb) callback parameter is not resolved to the module"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-30T23:14:30Z"
updated = "2026-10-30T23:39:25Z"
labels = ["audit:symbolic"]
scope = ["crates/grimble-bind/**", "crates/gob-symbols/src/lookups.rs", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "import('child_process').then(m => m.exec(x)) is a certain process.spawn use (or Unresolved when the callback is not an inline function); regression test pinned in crates/grimble-check/tests/symbolic_audit.rs"
bound = false
+++

Found by ~VNVD3Q1 probing. import('child_process').then(m => m.exec('x')) raises no CAP001 (neither certain nor unresolved), at top level and inside a function; the await form (const m = await import('child_process'); m.exec('x')) IS caught. Symbol-resolved fix required: bind the .then callback's first parameter to the import's module; if it cannot be resolved report Unresolved, never silent.
