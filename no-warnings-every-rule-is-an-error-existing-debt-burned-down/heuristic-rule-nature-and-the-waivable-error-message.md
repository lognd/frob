+++
id = "01M5XMJJ68A64KGZJGB291TPEB"
title = "Heuristic rule nature and the waivable-error message contract"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:02Z"
updated = "2026-10-28T12:55:41Z"
labels = ["no-story"]
scope = ["crates/gob-rules/**"]

[[acceptance]]
text = "Finding messages for nature=Heuristic rules state heuristic/smell, why it fired, and the exact frob:waive line with reason"
bound = false

[[acceptance]]
text = "Agent output says obey and do not waive and omits the waive line; human output shows it; reasonless waiver stays an Error"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.4). Filed from ~ZHW5Y2M.

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
