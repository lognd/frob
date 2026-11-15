+++
id = "01M7EXW5VKFRMY0HKECB4MM483"
title = "grimble-capabilities: match literal URL fetch() to net.connect grants (CAP001)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:22Z"
updated = "2026-11-15T06:21:22Z"
labels = ["no-story"]

[[acceptance]]
text = "A literal localhost URL is covered by the host:port grant"
bound = false

[[acceptance]]
text = "A non-matching host still raises CAP001"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md friction log. fetch("http://localhost:8000/...") is not matched to net.connect("localhost:8000").
