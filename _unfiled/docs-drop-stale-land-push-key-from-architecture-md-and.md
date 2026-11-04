+++
id = "01M6HTEHFGMTV8HV7NHK9TSFPH"
title = "Docs: drop stale [land] push key from architecture.md and distributed-tickets.md"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M5CWAYM0CCM0RR9KZ0HB0Z85"
reporter = "lognd"
created = "2026-11-03T23:03:31Z"
updated = "2026-11-04T00:00:37Z"
labels = ["good-first"]
scope = ["docs/design/architecture.md", "docs/design/frob/distributed-tickets.md"]

[[acceptance]]
text = 'Given the docs, when grepping for "[land] push", then no match remains and each site cites frob land --push'
bound = false
+++

## Start here

architecture.md:306 and distributed-tickets.md:101,657 cite a [land] push key. Replace with the frob land --push flag (see tickets.md section 10).
