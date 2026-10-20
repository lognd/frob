+++
id = "01M4052W6Q1FAQK362YF6RCGW1"
title = "Mirror run driver: blindness, recovery, work classes, feed and sweep assembled"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-03T05:51:39Z"
idempotency_key = "m2-mirror2-run"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/run.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX841SP0ZXM4CT18A4B8CV"

[[links]]
kind = "blocked-by"
target = "01M4052QSA5YKG6MY52BCW6PWV"

[[links]]
kind = "blocked-by"
target = "01M4052RC6C32957W1A9PYQAEE"

[[links]]
kind = "blocked-by"
target = "01M4052RW8F31VNBZ6AJM20TF3"

[[links]]
kind = "blocked-by"
target = "01M4052S04N2E2A08NNPAZKPYT"

[[links]]
kind = "blocked-by"
target = "01M4052S40VQGKG930DZPSM01K"

[[links]]
kind = "blocked-by"
target = "01M4052S7VEWJEYG78GNA1Z28V"

[[links]]
kind = "blocked-by"
target = "01M4052SBZCJ3MRHGTPAFW4QP1"

[[links]]
kind = "blocked-by"
target = "01M4052TC4BVA3JFFCHZX82EWS"

[[links]]
kind = "blocked-by"
target = "01M4052W2RYSRASA1PE0PRJJ1V"

[[acceptance]]
text = "Given work in all five classes, when a run executes against the fake adapter, then calls follow the class priority"
bound = false

[[acceptance]]
text = "Given a converged state, when a run executes, then no tracker mutation and no ledger commit happens"
bound = false

[[acceptance]]
text = "Given a failed blindness check, when a run starts, then nothing else runs and MIR001 token-blind is recorded"
bound = false

[[acceptance]]
text = "Given one ticket that cannot be rendered, when a run executes, then the other tickets are processed"
bound = false
+++

Implements mirror.md sections 3.1 to 3.4 (the loop).

One run: take the lock, blindness check, read the budget, execute the work classes in strict priority with the feed and the sweep, isolate failing tickets, commit progress, report. A run on a converged state changes nothing.
