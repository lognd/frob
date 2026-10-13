+++
id = "01M4V2A3VGST1NVJ0X7BR38TGJ"
title = "Regenerate stale generated docs on experimental (GEN001 CI red)"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-13T16:42:40Z"
updated = "2026-10-13T16:42:43Z"
idempotency_key = "gen001-2026-10-13"
scope = ["docs/**", "changelog.d/**"]

[[acceptance]]
text = "gen all --check is clean on experimental"
bound = false
+++
