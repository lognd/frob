+++
id = "01M625YH8QBYKZHCRTZDW0WFH0"
title = "org R4: move legacy rule files into src/rules per family (one PR per file)"
type = "task"
category = "todo"
priority = "medium"
points = 13
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:38Z"
updated = "2026-10-28T21:16:38Z"
idempotency_key = "org-R4"
scope = ["crates/frob-obligations/**"]

[[acceptance]]
text = "each legacy rules file is moved to src/rules/<id>.rs+.md, one move per PR, and its SPLIT_ALLOWED row removed; moved symbols acked"
bound = false
+++

Break: frob.lock symbols, frob:tests bindings; land only when no lease covers the files. Depends on R3. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
