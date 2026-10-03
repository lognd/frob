+++
id = "01M3Z714820D1SK6X44T9R1B70"
title = "G12: grimble.lock, grimble ack, SYS006-008"
type = "task"
category = "in-progress"
priority = "high"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-03T01:38:55Z"
idempotency_key = "m2-drift"
labels = ["milestone:2"]
scope = ["crates/grimble-bind/**", "crates/gob-lock/**", "crates/grimble/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713J7EDZCJSM7NWKASW54"

[[links]]
kind = "blocked-by"
target = "01M3Z71450ZE377RBK3EG1XSWC"

[[acceptance]]
text = "Given a producer whose Contract facet changed and a consumer acked at the old facet, when grimble check runs, then SYS006 names the flow and both ends"
bound = false
+++

G05 typed entries: contract skew over the Contract facet between producer and consumer, changed and renamed via identity and body facet, ack verb writing grimble.lock on the current branch.
