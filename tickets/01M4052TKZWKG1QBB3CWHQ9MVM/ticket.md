+++
id = "01M4052TKZWKG1QBB3CWHQ9MVM"
title = "frob ticket proposals accept: TTY, no agent marker, escaped diff, mapped identities, full value fetched"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-accept-guards"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/ticket/proposals_accept.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX855DB35XQZQPFKYWR6WX"

[[links]]
kind = "blocked-by"
target = "01M3ZXGAWKZPVY6HF9NJ8GAFQV"

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[links]]
kind = "blocked-by"
target = "01M4052SZYWSD45GEYNTTTJMDB"

[[acceptance]]
text = "Given no TTY or an agent marker, when accept runs, then it refuses and changes nothing"
bound = false

[[acceptance]]
text = "Given a proposal by an unmapped identity, when accept runs, then it refuses"
bound = false

[[acceptance]]
text = "Given a proposal on scope, acceptance, evidence or links, when accept runs, then it refuses to apply it"
bound = false

[[acceptance]]
text = "Given a proposal whose full value is gone from the tracker, when accept runs, then the proposal closes as unavailable"
bound = false

[[acceptance]]
text = "Given a valid proposal on a TTY, when accepted after the escaped diff is shown, then the field changes through a recorded event and proposal-accepted closes the proposal"
bound = false
+++

Implements mirror.md section 3.5 (accept guards) and security.md 2.11.

Accept inherits the old adopt guards: TTY only, never with an agent marker, shows the escaped diff, refuses edits by unmapped identities, never touches scope, acceptance, evidence or links. The full value is fetched at accept time; if it is gone the proposal closes as unavailable. The change is applied through normal ticket verbs as an event by the accepter citing the tracker user id.
