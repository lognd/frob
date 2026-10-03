+++
id = "01M4052S7VEWJEYG78GNA1Z28V"
title = "Create protocol: nonce, create-started journal, create-uncertain, recovery"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-create"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/create.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX851JW2KYRMCCK5RQKG5W"

[[links]]
kind = "blocked-by"
target = "01M4052QWSEERAG3JPCGXM4RK4"

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[links]]
kind = "blocked-by"
target = "01M4052RMBKXD6T8ANNFWJ751M"

[[acceptance]]
text = "Given a create that times out, when the ticket is processed again before recovery, then no second create is made for it"
bound = false

[[acceptance]]
text = "Given a create-uncertain ticket, when recovery lists the bot's issues back to the create's start time and matches the nonce, then the issue is adopted and the uncertainty is cleared"
bound = false

[[acceptance]]
text = "Given a late create landing after a retry (fake adapter), when the next run lists, then at most one extra issue exists for the ticket"
bound = false

[[acceptance]]
text = "Given a create, when it completes, then the history cursor taken before listing is the one stored (F3)"
bound = false
+++

Implements mirror.md section 3.3 (Create protocol; F3, F5).

Before a create the run derives a nonce and journals create started. A create with unknown outcome (timeout, 5xx, crash) makes the ticket create-uncertain: no further create for it until recovery has listed the bot's issues back to the create's start time and matched the nonce. GitHub's create has no idempotency key, so at most one extra issue per uncertain create is possible; the duplicates ticket closes it. The history cursor taken before the ticket's issues were listed is kept across the create.
