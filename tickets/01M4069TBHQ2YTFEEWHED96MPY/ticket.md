+++
id = "01M4069TBHQ2YTFEEWHED96MPY"
title = "PM013 WIP limit exceeded rule"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:55Z"
updated = "2026-10-03T15:28:20Z"
idempotency_key = "m2-rel-pm013"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/rules/wip.rs", "docs/reference/rules/pm/**"]

[[links]]
kind = "blocked-by"
target = "01M4069T76A6WSNHT3NZERXHAH"

[[acceptance]]
text = "Given three in-progress tickets and limit 2, when frob check runs, then PM013 fires naming the holders"
bound = false

[[acceptance]]
text = "Given two, when frob check runs, then PM013 is silent"
bound = false
+++

Fires when the in-progress count exceeds [pm.wip] in_progress (expedite tickets counted separately, section classes) or a category limit; the message names the holders. Reads the ledger index only.
