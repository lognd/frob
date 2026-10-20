+++
id = "01M3AXSD8ZBKX66VDWJCG6SX2W"
title = "dropped: approaching/exceeding the 16MB BSON document size limit by embedding"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6431"]
labels = ["milestone:0.538.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Document anti-pattern #2. Authority: MongoDB Manual,
"MongoDB Limits and Thresholds": "The maximum BSON document size is 16
mebibytes... To store documents larger than the maximum size, MongoDB
provides the GridFS API" --
https://www.mongodb.com/docs/manual/reference/limits/. Static tier:
"dynamic-only (size is a runtime property; linter can only flag
embedding-without-bound patterns as a proxy, same as #1)" -- the proxy
(unbounded array growth) is ALREADY filed as STORE1's unbounded-array-
growth row (folded into the STORE1xx group's mongo leaves); filing a
SECOND rule for the same proxy shape under a different id would
duplicate STORE105/STORE1xx's array-growth coverage rather than add a
genuinely new static signal.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
