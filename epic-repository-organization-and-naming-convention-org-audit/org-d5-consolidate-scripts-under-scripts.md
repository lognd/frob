+++
id = "01M625YJGQ342AM88T5XY2G858"
title = "org D5: consolidate scripts under scripts/"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:39Z"
updated = "2026-10-28T21:16:39Z"
idempotency_key = "org-D5"
scope = ["scripts/**"]

[[acceptance]]
text = "scripts live under scripts/{ci,hooks,packaging}; workflows, release.yml and hook install paths updated and tested"
bound = false
+++

Hidden consumers: workflows, packaging smoke, user .claude hooks. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
