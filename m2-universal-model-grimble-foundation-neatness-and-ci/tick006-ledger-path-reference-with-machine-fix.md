+++
id = "01M3ZX86MA30ABW915Z943BQYB"
title = "TICK006 ledger-path-reference with machine fix"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-11T19:02:56Z"
idempotency_key = "m2-nav-tick004"
labels = ["milestone:2", "area:navigation", "creates:crates/frob-obligations/src/tick_paths.rs"]
scope = ["crates/frob-obligations/src/tick_paths.rs", "crates/frob-ledger/src/mirror_map.rs", "crates/frob-obligations/src/lib.rs", "crates/frob-obligations/src/rules.rs", "crates/frob-obligations/tests/mdtest/tick006.md", "crates/frob-check/src/filecheck.rs", "crates/gob-check/src/applicability.rs", "crates/frob/tests/ticket_path_refs.rs", "docs/reference/rules/**", "docs/design/navigation.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M3ZX82K7HX9D2VKT25KS4MV2"

[[acceptance]]
text = "Given a doc linking a GitHub blob URL that points into the ticket branch, when check runs, then TICK006 fires and `--fix` rewrites it to the ticket ULID"
bound = true

[[acceptance]]
text = "Given generated pages that use relative paths, when check runs, then TICK006 does not fire"
bound = true
+++

Implements navigation.md sections 1 and 6.

Error, P+: tracked hand-written text links to a ticket-branch path (<epic>/<slug>.md, a blob or tree URL on the ticket branch, or the old tickets/<ULID>/ticket.md); the machine fix rewrites it to the ULID; runs over the code repository and the hand-written files of the ticket branch.
