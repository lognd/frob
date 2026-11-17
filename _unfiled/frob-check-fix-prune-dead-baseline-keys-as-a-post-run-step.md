+++
id = "01M7KME8CB19VZP2A6F8SR8GZ9"
title = "frob check --fix: prune dead baseline keys as a post-run step"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-17T02:12:40Z"
updated = "2026-11-17T03:49:46Z"
idempotency_key = "split-8az7dkd-fix"

[[acceptance]]
text = "Given dead baseline keys, when frob check --fix runs a full unscoped check, then frob-baseline.toml is pruned of dead keys and a second run changes nothing"
bound = true
+++
