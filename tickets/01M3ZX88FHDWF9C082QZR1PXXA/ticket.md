+++
id = "01M3ZX88FHDWF9C082QZR1PXXA"
title = "frob ticket url <id>"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:47Z"
updated = "2026-10-11T20:52:24Z"
idempotency_key = "m2-nav-ticket-url"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/ticket/url_cmd.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/tests/ticket_url.rs", "crates/gob-dev/profile.toml", "docs/guides/ticket-branch.md", "docs/reference/cli/frob.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M4M85N13CXXPTEE7PYVCV0NS"

[[acceptance]]
text = "Given a ticket on the branch, when `frob ticket url ~X` runs, then the blob URL on frob-tickets with the current path is printed"
bound = true

[[acceptance]]
text = "Given a mirrored ticket, when run, then the issue URL is printed as well"
bound = true
+++

Implements navigation.md section 1 (last bullet).

Prints the current web URL of the ticket file on the ticket branch and of the mirrored issue when one exists.
