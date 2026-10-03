+++
id = "01M3ZX7SCND92D383E8X9CEWJ7"
title = "wasmtime component host: instantiate, epoch budgets, traps and budget to Unresolved"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:32Z"
updated = "2026-10-03T03:34:32Z"
idempotency_key = "m2-wasm-host"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-wasm/src/host/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S1ZBWEC0PE895ZC6KXN"

[[links]]
kind = "blocked-by"
target = "01M3ZX7S5JYVCTRD0ZYC57GJ93"

[[links]]
kind = "blocked-by"
target = "01M3ZX7S93E1FRRMBDPGAGAM2H"

[[acceptance]]
text = "Given a component that loops forever, when called, then the call is cancelled and its rules report Unresolved budget for that file"
bound = false

[[acceptance]]
text = "Given a component that traps, when called, then Unresolved trap is reported and other files still run"
bound = false
+++

Implements plugins.md sections 6.4 and 6.5; security.md section 2.5.

Runs inside the sandbox worker only. Epoch interruption; a call over [packs] file_budget_ms reports Unresolved reason budget, a trap reports Unresolved reason trap. Never silence.
