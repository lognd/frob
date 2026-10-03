+++
id = "01M4052RRC7X5Y23PNBDKR9V6W"
title = "Budget planner: rate-limit headers, share, create and mutation caps, spacing"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-budget"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/budget.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052QNSFSWV0SQ0A05XQ12K"

[[acceptance]]
text = "Given 5000 remaining and the default share, when the run starts, then at most 2500 calls, 50 creates and 300 mutations are planned"
bound = false

[[acceptance]]
text = "Given a remaining budget below one ticket's reads plus one write, when planned, then the run reports MIR001 budget-too-small and makes no write"
bound = false

[[acceptance]]
text = "Given missing rate-limit headers, when the run starts, then it stops with MIR001 and the reason"
bound = false
+++

Implements mirror.md section 3.2 (Budget planner; F8).

At start the run reads the rate-limit headers and spends at most a configured share (default half) of what remains, at most C creates (default 50) and M mutations (default 300), serially with at least one second between mutations. The budget must cover one ticket's reads plus one write, else MIR001 budget-too-small.
