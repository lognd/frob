+++
id = "01M4052V7BG4YBHSW863YZEJ9X"
title = "frob mirror recreate <ticket>"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-recreate"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/mirror_recreate_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052QSA5YKG6MY52BCW6PWV"

[[links]]
kind = "blocked-by"
target = "01M4052S7VEWJEYG78GNA1Z28V"

[[acceptance]]
text = "Given a ticket marked unmirrored after a 410, when `frob mirror recreate` runs, then a new issue is created through the create protocol and the shard points at it"
bound = false

[[acceptance]]
text = "Given a ticket whose issue merely returned 404, when the verb runs, then it refuses and says the issue may be invisible, not deleted"
bound = false
+++

Implements mirror.md section 3.3 (the mirror never recreates an issue without a person running recreate).

A person runs the verb for a ticket marked unmirrored (410); it goes through the create protocol and the ticket becomes mirrored again.
