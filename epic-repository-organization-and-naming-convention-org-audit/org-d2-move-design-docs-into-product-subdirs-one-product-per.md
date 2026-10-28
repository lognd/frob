+++
id = "01M625YJ7HSYVD0SBKMZ3H5THZ"
title = "org D2: move design docs into product subdirs (one product per PR)"
type = "task"
category = "todo"
priority = "low"
points = 8
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:39Z"
updated = "2026-10-28T21:16:39Z"
idempotency_key = "org-D2"
scope = ["docs/design/**"]

[[acceptance]]
text = "design docs live under docs/design/<product>/ with MOVED.toml rows; frob doc remap run; DRIFT acks reviewed"
bound = false
+++

HIGH RISK: external URLs and frob:doc bindings; do not start early. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
