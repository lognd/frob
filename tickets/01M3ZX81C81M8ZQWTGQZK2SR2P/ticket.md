+++
id = "01M3ZX81C81M8ZQWTGQZK2SR2P"
title = "doctor and a TICK rule check ledger-branch protection through the hosting API"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-20T04:50:14Z"
idempotency_key = "m2-sec-ledger-protect"
labels = ["milestone:2", "area:security"]
scope = ["crates/frob/src/doctor.rs", "crates/frob-obligations/src/tick_protect.rs", "crates/frob-obligations/src/lib.rs", "crates/frob-obligations/Cargo.toml", "crates/frob/Cargo.toml", "crates/frob/src/mirror_recreate_cmd.rs", "Cargo.lock", "docs/design/navigation.md", "docs/reference/rules/*"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[acceptance]]
text = "Given a hosting API answering that force pushes are allowed on frob-tickets, when doctor runs, then an Error is reported"
bound = true

[[acceptance]]
text = "Given no token or an unreachable API, when doctor runs, then the result is Unresolved, not clean"
bound = true
+++

Implements security.md section 2.11.

Error where the API answers that force pushes or deletion are allowed; Unresolved where it cannot answer.
