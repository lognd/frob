+++
id = "01M5F4J8QW4YYD20XP8KGTC9X2"
title = "Python adapter misses call nested in return inside def (r.keys)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T11:46:53Z"
updated = "2026-11-01T22:23:17Z"
scope = ["crates/gob-plan/src/exec/core/field.rs", "crates/gob-plan/src/exec/core/kind.rs", "crates/gob-plan/tests/stmt_kinds.rs", "changelog.d/01M5F4J8QW4YYD20XP8KGTC9X2.changed.md"]
+++

Found by sysdesign STORE101: 'return r.keys("session:*")' inside a def did not match c.callee.name == "keys"; a bare statement call does. Investigate the python adapter call extraction.
