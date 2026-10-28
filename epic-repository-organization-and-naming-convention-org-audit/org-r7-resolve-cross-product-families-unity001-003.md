+++
id = "01M625YHF7Z9JYN8VPGG4AHG0P"
title = "org R7: resolve cross-product families (UNITY001-003, WEBPERF2xx) with renamed aliases"
type = "task"
category = "todo"
priority = "low"
points = 8
parent = "01M61MHM8ER57BA9VVKXDTE2G7"
reporter = "lognd"
created = "2026-10-28T21:16:38Z"
updated = "2026-10-28T21:16:38Z"
idempotency_key = "org-R7"
scope = ["crates/gob-rules/**"]

[[acceptance]]
text = "UNITY and WEBPERF2xx owned by one product each; old ids resolve through tested aliases incl. frob:accept and config overrides"
bound = false
+++

HIGH RISK: do last, not early. Owner decision needed on target names. Depends on R3 and R4. Org audit section 4.7 (scratchpad org-audit.md). Deferred and sequenced, not dropped.
