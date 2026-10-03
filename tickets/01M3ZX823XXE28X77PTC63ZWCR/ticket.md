+++
id = "01M3ZX823XXE28X77PTC63ZWCR"
title = "fix --interactive: review maybe-incorrect fixes on a TTY"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-03T03:34:41Z"
idempotency_key = "m2-diag-fix-interactive"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/frob/src/fix_cmd.rs", "crates/gob-cli/src/interactive.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7E968R74N08V8DW4RJVG"

[[links]]
kind = "blocked-by"
target = "01M3ZX7Z0EM0DCAHC59PJH50MJ"

[[links]]
kind = "blocked-by"
target = "01M3ZX81T4DCMKXZXNSR5QDX7H"

[[acceptance]]
text = "Given a non-TTY stdin, when `frob fix --interactive` runs, then it exits 2 and names the JSON fix list"
bound = false

[[acceptance]]
text = "Given a TTY and a maybe-incorrect fix, when the user answers y, then the edit is applied and journaled; answering s skips the whole rule"
bound = false
+++

Implements diagnostics.md section 4.

One fix at a time with a diff and [y]es / [n]o / [e]dit / [s]kip rule / [q]uit; refuses with exit 2 when stdin or stdout is not a TTY and points at the JSON fix list; invisible characters shown as escapes.
