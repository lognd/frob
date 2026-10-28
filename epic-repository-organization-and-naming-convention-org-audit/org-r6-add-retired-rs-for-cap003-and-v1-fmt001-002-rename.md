+++
id = "01M625YHC6B6GPQ8573B7EJ1YK"
title = "org R6: add retired.rs for CAP003 and v1 FMT001/002; rename GRL compiler codes to E-GRL-NNN"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:38Z"
updated = "2026-10-28T21:16:38Z"
idempotency_key = "org-R6"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "retired ids recorded in retired.rs and cannot be reused; GRL compiler codes are E-GRL-NNN and docs regenerate clean"
bound = false
+++

Breaks tests/docs matching GRL0NN strings. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
