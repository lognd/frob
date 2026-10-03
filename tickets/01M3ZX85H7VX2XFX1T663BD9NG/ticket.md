+++
id = "01M3ZX85H7VX2XFX1T663BD9NG"
title = "E-TICKET-PATH: refuse a file path where a ticket id is expected"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-nav-e-ticket-path"
labels = ["milestone:2", "area:navigation", "good-first"]
scope = ["crates/frob/src/ticket/read.rs", "crates/gob-cli/src/error.rs"]

[[acceptance]]
text = "Given `frob ticket show tickets/01M3.../ticket.md`, when run, then it exits 2 with E-TICKET-PATH naming the handle of that ticket"
bound = false

[[acceptance]]
text = "Given a valid handle, ULID or alias, when run, then behaviour is unchanged"
bound = false
+++

Implements navigation.md sections 1 and 6.

A CLI argument that names a ticket file is refused with the id it names: `that file is ~6C0D1E2; pass the id`.

## Start here
Read navigation.md section 1 (table row CLI arguments) and crates/frob/src/ticket/read.rs where ids are resolved. Test: `cargo nextest run -p frob`. Ask: the repository owner (Logan) in a comment on this ticket.
