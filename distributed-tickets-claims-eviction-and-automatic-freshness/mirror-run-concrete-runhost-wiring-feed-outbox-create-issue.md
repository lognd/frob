+++
id = "01M5EA0YFAACDY5BV70R2MH98S"
title = "mirror run: concrete RunHost wiring feed, outbox, create_issue, recover, reconcile, close_duplicates"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:03:03Z"
updated = "2026-10-21T04:15:14Z"
+++

run.rs defines the RunHost trait only; implement it against the real mirror modules.
