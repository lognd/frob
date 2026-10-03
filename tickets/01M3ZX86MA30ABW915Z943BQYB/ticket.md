+++
id = "01M3ZX86MA30ABW915Z943BQYB"
title = "TICK004 ledger-path-reference with machine fix"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-tick004"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-obligations/src/tick_paths.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M3ZX82K7HX9D2VKT25KS4MV2"

[[acceptance]]
text = "Given a doc linking `https://github.com/o/r/blob/frob-tickets/parser-rewrite/x.md`, when check runs, then TICK004 fires and `--fix` rewrites it to the ticket ULID"
bound = false

[[acceptance]]
text = "Given generated pages that use relative paths, when check runs, then TICK004 does not fire"
bound = false
+++

Implements navigation.md sections 1 and 6.

Error, P+: tracked hand-written text links to a ticket-branch path (<epic>/<slug>.md, a blob or tree URL on the ticket branch, or the old tickets/<ULID>/ticket.md); the machine fix rewrites it to the ULID; runs over the code repository and the hand-written files of the ticket branch.
