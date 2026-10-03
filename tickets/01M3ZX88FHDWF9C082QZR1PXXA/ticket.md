+++
id = "01M3ZX88FHDWF9C082QZR1PXXA"
title = "frob ticket url <id>"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-03T03:34:47Z"
idempotency_key = "m2-nav-ticket-url"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/ticket/url_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[acceptance]]
text = "Given a ticket on the branch, when `frob ticket url ~X` runs, then the blob URL on frob-tickets with the current path is printed"
bound = false

[[acceptance]]
text = "Given a mirrored ticket, when run, then the issue URL is printed as well"
bound = false
+++

Implements navigation.md section 1 (last bullet).

Prints the current web URL of the ticket file on the ticket branch and of the mirrored issue when one exists.
