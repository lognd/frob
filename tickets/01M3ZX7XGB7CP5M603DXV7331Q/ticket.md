+++
id = "01M3ZX7XGB7CP5M603DXV7331Q"
title = "GATE001 policy-weakened (Error, required)"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:36Z"
updated = "2026-10-03T03:34:36Z"
idempotency_key = "m2-sec-gate001"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-check/src/gate001.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7X3RQTTR7V8JFRN8TQEK"

[[links]]
kind = "blocked-by"
target = "01M3ZX7XBY8S4DXNFVYWVF8884"

[[acceptance]]
text = "Given a head that sets a rule severity from error to warn, when check --base runs, then GATE001 names old and new value"
bound = false

[[acceptance]]
text = "Given a head that strengthens policy, when run, then no GATE001 is emitted"
bound = false
+++

Implements security.md sections 2.7 and 4.

One finding per weakening naming old and new value; strengthening is silent; cleared only by an exception with a ticket or a reviewer label.
