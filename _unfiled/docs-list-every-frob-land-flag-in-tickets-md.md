+++
id = "01M6HTEHJDTS3RMZHP0C74E7Q2"
title = "Docs: list every frob land flag in tickets.md"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 1
parent = "01M5CWAYM0CCM0RR9KZ0HB0Z85"
reporter = "lognd"
created = "2026-11-03T23:03:31Z"
updated = "2026-11-04T15:08:30Z"
labels = ["good-first"]
scope = ["docs/design/frob/tickets.md"]

[[acceptance]]
text = "Given tickets.md, when compared with frob land --help, then every flag is documented"
bound = true
+++

## Start here

Run frob land --help, diff against the land section of cli.md, add any missing flag (--push, --wait, --override-base-ci, --reason).
