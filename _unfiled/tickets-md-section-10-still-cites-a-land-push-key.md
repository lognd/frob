+++
id = "01M5CWAYM0CCM0RR9KZ0HB0Z85"
title = "tickets.md section 10 still cites a [land] push key"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T14:44:36Z"
updated = "2026-11-03T22:30:30Z"
labels = ["good-first", "no-story"]
scope = ["docs/design/tickets.md", "docs/design/frob/tickets.md"]

[[acceptance]]
text = "Given docs/design/tickets.md section 10, when a reader looks for the push setting, then it cites the frob land --push flag and no [land] push key"
bound = false
+++

Found while working ~9XM2VJC: docs/design/tickets.md line ~754 says "Push is opt-in ([land] push)"; no such config key exists (LandConfig in crates/frob-land/src/base_ci.rs has none; push is the frob land --push flag).

## Start here

Open docs/design/tickets.md near line 754 and reword the sentence to name the --push flag.
