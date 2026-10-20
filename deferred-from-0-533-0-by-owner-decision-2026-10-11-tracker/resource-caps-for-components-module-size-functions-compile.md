+++
id = "01M3ZX7S93E1FRRMBDPGAGAM2H"
title = "Resource caps for components: module size, functions, compile time, memory, epoch"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:31Z"
updated = "2026-10-03T03:34:31Z"
idempotency_key = "m2-sec-wasm-caps"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-wasm/src/limits.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S1ZBWEC0PE895ZC6KXN"

[[acceptance]]
text = "Given a module over the size cap, when loaded, then it is rejected with Unresolved budget"
bound = false

[[acceptance]]
text = "Given a component over the memory cap, when run, then the call is cancelled and reported"
bound = false
+++

Implements security.md section 2.5 (resource caps).

Caps checked before results cross back; breach is Unresolved budget.
