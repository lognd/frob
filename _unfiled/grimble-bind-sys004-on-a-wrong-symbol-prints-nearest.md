+++
id = "01M7EXVKHQCS5G8AC46D7F0A0X"
title = "grimble-bind: SYS004 on a wrong symbol prints nearest identities"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:03Z"
updated = "2026-11-15T06:21:03Z"
labels = ["no-story"]

[[acceptance]]
text = "A SYS004 on a near-miss symbol names the closest identity"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md L6. SYS004 gives no hint (the identity is Shell[Plugin].run). Remedy: print nearest identities or add a doctor section.
