+++
id = "01M7EXVM8745D3GF4AD1HH47GP"
title = "grimble-lints: collapse PATH002/PATH003/TIME001/TIME002 Unresolved to one per rule per language"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:04Z"
updated = "2026-11-15T06:21:04Z"
labels = ["no-story"]

[[acceptance]]
text = "A repo of N ts files yields one Unresolved per rule"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md L10. Four Unresolved lines per .ts/.tsx file. Crates: grimble-lints path.rs, time_pass.rs.
