+++
id = "01M3ZX7VJE22Y68R184Y9WQC2N"
title = "Tool stages as argv templates with typed placeholders"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-03T03:34:34Z"
idempotency_key = "m2-sec-argv-templates"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-check/src/tools.rs", "crates/gob-check/src/config.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7J6SES21T3KC4WESVR7H"

[[acceptance]]
text = "Given a stage whose command is a shell string or a bare name with no template, when loaded, then it is a CFG error naming the stage"
bound = false

[[acceptance]]
text = "Given a placeholder typed tracked path and a path outside the tracked set, when expanded, then the stage is refused"
bound = false
+++

Implements security.md section 2.4.

[[check.tool]] stages are a fixed program, fixed flags and typed placeholders such as a tracked path; never a bare name or a shell string.
