+++
id = "01M64230KYDRZ7V51SECS763EX"
title = "LOG: JavaScript computed, destructured, dynamic and reflective output forms are not resolved"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-30T03:15:08Z"
idempotency_key = "vnvd3q1-log-js"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/grimble-bind/**", "docs/design/output-atoms.md", "changelog.d/01M64230KYDRZ7V51SECS763EX.changed.md"]

[[acceptance]]
text = "computed member names, nested destructuring, parameter defaults, with-blocks, dynamic import, eval/Function, Reflect, process internals and fs writeSync to fd 1 or 2 are resolved or reported Unresolved"
bound = true
+++

Cases js02 js03 js04 js05 js08 js09 js10 js12 js14 js15. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently
