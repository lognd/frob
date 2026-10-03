+++
id = "01M3ZX864QGR220FTRGCDPXYZD"
title = "Generated indexes: status, milestone, component, ready, blocked, recent, done by month"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-gen-indexes"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/indexes.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a ledger with blocked and doable tickets, when generated, then ready.md lists only unblocked doable tickets ranked by priority and blocked.md names each blocker"
bound = false

[[acceptance]]
text = "Given 80 events, when recent.md is generated, then it lists the last 50"
bound = false
+++

Implements navigation.md section 3.1.

indexes/by-status.md, by-milestone.md, by-component.md, ready.md (doable and unblocked, ranked), blocked.md, recent.md (last 50 events), done/<YYYY-MM>.md and the indexes/README.md map; pages are capped.
