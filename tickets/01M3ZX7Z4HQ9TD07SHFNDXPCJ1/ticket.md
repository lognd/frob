+++
id = "01M3ZX7Z4HQ9TD07SHFNDXPCJ1"
title = "Text renderer labels non-host text with its origin"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:37Z"
updated = "2026-10-03T03:34:37Z"
idempotency_key = "m2-sec-origin-render"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-diagnostics/src/text.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7YW7S3BJ72FPRQ85F72V"

[[links]]
kind = "blocked-by"
target = "01M3ZX7Z0EM0DCAHC59PJH50MJ"

[[acceptance]]
text = "Given a pack message, when rendered as text, then it is prefixed with `pack(NAME) says:`"
bound = false

[[acceptance]]
text = "Given a host message, when rendered, then no prefix is added"
bound = false
+++

Implements security.md section 2.10 (origin).

Text mode prefixes non-host text, e.g. `pack(py-safety) says:`.
