+++
id = "01M7EXXQCYKFDT9N8JZN3VS486"
title = "grimble: gate NAME owner= until= [kill_switch] expiring inventory and readiness pack (G10,G11,G12)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:22:12Z"
updated = "2026-11-15T06:22:12Z"
labels = ["no-story"]

[[acceptance]]
text = "Expired gate is an Error"
bound = false

[[acceptance]]
text = "Duplicate flag binding is an Error"
bound = false

[[acceptance]]
text = "A readiness pack is documented"
bound = false
+++

Research: ~/projects/frob-research-lifecycle.md rec 9. Expired gate and a flag bound to two scenarios are Errors. Log and metric atoms count as observable effects on end err paths (open question 23).
