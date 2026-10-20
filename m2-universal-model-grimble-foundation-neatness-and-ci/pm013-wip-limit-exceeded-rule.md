+++
id = "01M4069TBHQ2YTFEEWHED96MPY"
title = "PM013 WIP limit exceeded rule"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:55Z"
updated = "2026-10-03T15:49:51Z"
idempotency_key = "m2-rel-pm013"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/rules/wip.rs", "docs/reference/rules/pm/**", "crates/frob-check/src/product.rs", "crates/frob-pm/src/rules/mod.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-pm/tests/mdtest/pm013.md", "docs/reference/rules/PM013.md", "docs/reference/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M4069T76A6WSNHT3NZERXHAH"

[[acceptance]]
text = "Given three in-progress tickets and limit 2, when frob check runs, then PM013 fires naming the holders"
bound = true

[[acceptance]]
text = "Given two, when frob check runs, then PM013 is silent"
bound = true
+++

Fires when the in-progress count exceeds [pm.wip] in_progress (expedite tickets counted separately, section classes) or a category limit; the message names the holders. Reads the ledger index only.
