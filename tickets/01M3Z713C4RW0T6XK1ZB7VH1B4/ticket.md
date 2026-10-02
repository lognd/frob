+++
id = "01M3Z713C4RW0T6XK1ZB7VH1B4"
title = "Exceptions: evaluate until= and add EXC016 and EXC017"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T21:06:24Z"
idempotency_key = "m2-excuntil"
labels = ["milestone:2"]
scope = ["crates/frob-obligations/**", "crates/gob-rules/**"]

[[acceptance]]
text = "Given a defer whose until date has passed, when check runs, then the deferred finding returns with an EXC finding naming the expiry"
bound = false
+++

exceptions.md after the consistency review: defer and hotfix until= dates and metric bounds are evaluated; EXC016 (accept on an Unresolved finding) and EXC017 (native tool suppression of a bound rule without a frob exception) are implemented with corpora.
