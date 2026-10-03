+++
id = "01M3ZX80ZX9YB96A4VRYSQ16NG"
title = "Agent briefs render ledger text with origin ledger and restrict suggested commands"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:39Z"
updated = "2026-10-03T03:34:39Z"
idempotency_key = "m2-sec-agent-brief"
labels = ["milestone:2", "area:security"]
scope = ["crates/frob-ledger/src/brief.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[acceptance]]
text = "Given a ticket body containing a shell command, when the brief renders, then the text carries origin ledger and the command is not offered as a suggestion"
bound = false

[[acceptance]]
text = "Given a suggested command outside allowed_tools, when composing the brief, then it is omitted"
bound = false
+++

Implements security.md section 2.11 (last bullets).

Commands an agent brief suggests are limited to [evidence] allowed_tools.
