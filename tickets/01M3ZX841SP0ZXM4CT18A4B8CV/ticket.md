+++
id = "01M3ZX841SP0ZXM4CT18A4B8CV"
title = "Outbox: ledger-driven work from unpublished events, idempotent set-to-value operations, full resync"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T05:51:54Z"
idempotency_key = "m2-mirror-outbox"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/outbox.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[links]]
kind = "blocked-by"
target = "01M3ZX83XX6D2N7XDTVRVYV6TS"

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[acceptance]]
text = "Given a run interrupted after two of five operations, when rerun, then only the remaining three execute and nothing is duplicated"
bound = false

[[acceptance]]
text = "Given no new events, when the mirror runs, then no tracker request that mutates state is made"
bound = false
+++

Implements mirror.md sections 3.2 (work class 2) and 3.4.

Each ledger event needing publishing becomes an operation keyed by ticket ULID plus event ULID. Operations are set-field-to-value, so a replay or a late duplicate is harmless; an operation whose value equals the tracker's normalized current value is skipped; failures retry next run; incremental by default, with a full-resync mode that diffs every ticket within the budget over several runs. Ordering within the class is oldest first with round-robin resumption (m2-mirror2-work-classes).
