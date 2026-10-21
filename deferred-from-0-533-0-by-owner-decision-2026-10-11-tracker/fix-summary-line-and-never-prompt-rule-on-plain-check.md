+++
id = "01M3ZX81ZPA8J5RXBEZ14SZNSZ"
title = "Fix summary line and never-prompt rule on plain check"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-21T03:15:58Z"
idempotency_key = "m2-diag-fix-summary"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/frob-check/src/summary.rs", "crates/frob-check/src/lib.rs", "crates/frob-check/src/verb.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX81T4DCMKXZXNSR5QDX7H"

[[acceptance]]
text = "Given three fixes of which one is machine, when check runs on a TTY, then the summary ends with the documented line and no prompt appears"
bound = false

[[acceptance]]
text = "Given a plain check, when it finishes, then the work tree is byte-identical to before"
bound = false
+++

Implements diagnostics.md section 4.

A plain check changes nothing and never prompts; the summary ends with `3 fixes available (1 safe): run frob check --fix, or frob fix --interactive to review the rest`.
