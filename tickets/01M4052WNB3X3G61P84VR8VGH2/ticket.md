+++
id = "01M4052WNB3X3G61P84VR8VGH2"
title = "Property tests: budget and starvation (L3, S7, round-robin)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:40Z"
updated = "2026-10-03T05:51:40Z"
idempotency_key = "m2-mirror2-prop-budget"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/tests/prop_budget.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052W6Q1FAQK362YF6RCGW1"

[[links]]
kind = "blocked-by"
target = "01M4052WAB3H52W92NYG3AS571"

[[acceptance]]
text = "Given two tickets, edits that never stop and a budget of reads plus one write, when runs repeat, then every ticket completes in every rotation and no edit is lost"
bound = false

[[acceptance]]
text = "Given a budget below one ticket's reads plus one write, when a run starts, then MIR001 budget-too-small is reported and nothing is written"
bound = false

[[acceptance]]
text = "Given any scenario, when a run executes, then tracker mutations stay within the budget and the C and M caps"
bound = false
+++

Implements mirror.md section 3.7 (budget row, unbounded-edits row) and the model README sections 5 and 6.3.

With round-robin order and a budget of one ticket's reads plus one write, every ticket completes infinitely often under unbounded edits and every edit is recorded; with a fixed order or a budget below that minimum the tests show the documented failures (F8, B3, MC_Race cases) as expected-failure scenarios.
