+++
id = "01M3ZX81T4DCMKXZXNSR5QDX7H"
title = "check --fix applies machine fixes within the ticket scope"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:40Z"
updated = "2026-10-03T03:35:00Z"
idempotency_key = "m2-diag-fix-scope"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/frob-check/src/fix.rs", "crates/frob-check/src/scope.rs"]

[[links]]
kind = "blocked-by"
target = "01M3Z71361PCFXV5VKSACRF17G"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E968R74N08V8DW4RJVG"

[[links]]
kind = "relates"
target = "01M3Z71361PCFXV5VKSACRF17G"

[[acceptance]]
text = "Given a machine fix on a file outside the lease, when `check --fix` runs in the ticket worktree, then the file is unchanged and the skipped fix is listed with `frob lease widen`"
bound = false

[[acceptance]]
text = "Given a machine fix inside the scope, when run, then the edit is applied once, affected rules re-run once, and the summary lists the files changed and what remains"
bound = false
+++

Implements diagnostics.md section 3; owner decision 7.2.

Inside a ticket worktree --fix edits only files in the ticket scope (plus generated files the scope owns) and lists skipped out-of-scope fixes with the command that would widen the scope (frob lease widen); outside a ticket only the paths the check was asked to cover. --fix --unsafe is not offered.
