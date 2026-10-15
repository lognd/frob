+++
id = "01M3ZX7X3RQTTR7V8JFRN8TQEK"
title = "Required packs: required Unresolved reasons for unfinished plugins"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-15T06:04:26Z"
idempotency_key = "m2-sec-required-packs"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-diagnostics/src/required.rs", "crates/gob-rules/src/required.rs", "crates/gob-rules/src/lib.rs", "crates/grimble-check/src/sibling.rs", "docs/schemas/envelope.json", "docs/schemas/sibling.json"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7JWHQZQHD66HV2SB0498"

[[acceptance]]
text = "Given a required pack that traps, when check runs, then the Unresolved is required and exits 1 under fail_on_unresolved=required"
bound = true

[[acceptance]]
text = "Given the same pack not marked required, when it traps, then the Unresolved does not fail the gate"
bound = true
+++

Implements security.md section 2.7 (I9).

`[[packs.enable]] required = true` (materialized, per pack and per rule): untrusted, untrusted-in-change, budget, trap, effect-denied and pack-unavailable become required with matching RequiredReason variants.
