+++
id = "01M3ZX86R5V67MT726K3X7KVWM"
title = "TICK005 reindex-not-pure: replay check"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-tick005"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-obligations/src/tick_reindex.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85X37W6QSQSJD1WYVKZG"

[[acceptance]]
text = "Given a reindex commit with one hand-edited ticket body, when checked, then TICK005 fires"
bound = false

[[acceptance]]
text = "Given a reindex commit whose trailer names an unavailable frob version, when checked, then the result is Unresolved generator-version"
bound = false
+++

Implements navigation.md section 2.2.

Replay the reindex in memory on the parent commit's tree with the frob version named in the trailer; the tree id must equal the commit's. When that version is unavailable the result is Unresolved reason generator-version.
