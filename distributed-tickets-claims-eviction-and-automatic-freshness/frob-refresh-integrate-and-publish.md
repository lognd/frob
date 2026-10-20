+++
id = "01M5CW049SPSRGGP5ENQD7BPB3"
title = "frob refresh: integrate and publish"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T17:15:15Z"
idempotency_key = "dt-DT06"

[[links]]
kind = "blocked-by"
target = "01M5CW03W58HQWBGDANP418XYE"

[[links]]
kind = "blocked-by"
target = "01M5CW046DKVK5QSJR8TMEN0F2"
+++

Fetch changed refs, plumbing union merge with conflict report and integrity gate, CAS push, safe base fast-forward. Verb is frob refresh (not sync; avoids frob agent sync). See docs/design/distributed-tickets.md.
