+++
id = "01M3ZX883TDB46GGDYS92KDR1Q"
title = "ticket new --good-first scaffolds the Start here section"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-03T03:34:47Z"
idempotency_key = "m2-nav-good-first-flag"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/ticket/write.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX87KRP6G49GHANMAK5JA8"

[[acceptance]]
text = "Given `frob ticket new --good-first --title X`, when run, then the ticket has the label and a `## Start here` scaffold"
bound = false

[[acceptance]]
text = "Given the scaffold left unfilled, when check runs, then PM031 reports the placeholders"
bound = false
+++

Implements navigation.md section 4.2.

Adds the label and a body scaffold naming files to read, the test command and who to ask.
