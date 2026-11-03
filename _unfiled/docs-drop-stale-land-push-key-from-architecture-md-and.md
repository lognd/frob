+++
id = "01M6HTEHFGMTV8HV7NHK9TSFPH"
title = "Docs: drop stale [land] push key from architecture.md and distributed-tickets.md"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M5CWAYM0CCM0RR9KZ0HB0Z85"
reporter = "lognd"
created = "2026-11-03T23:03:31Z"
updated = "2026-11-03T23:04:54Z"
labels = ["good-first"]
scope = ["docs/design/architecture.md"]

[[acceptance]]
text = "No doc cites a [land] push key; each cites frob land --push instead"
bound = false
+++

## Start here

architecture.md:306 and distributed-tickets.md:101,657 cite a [land] push key. Replace with the frob land --push flag (see tickets.md section 10).
