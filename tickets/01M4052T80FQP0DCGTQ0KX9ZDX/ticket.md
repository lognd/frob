+++
id = "01M4052T80FQP0DCGTQ0KX9ZDX"
title = "Proposal expiry after proposal_ttl_days"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-proposal-expire"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/expire.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052SZYWSD45GEYNTTTJMDB"

[[links]]
kind = "blocked-by"
target = "01M4052T420AX728KKZ2RDYSTX"

[[acceptance]]
text = "Given a pending proposal older than proposal_ttl_days, when a run ends, then a proposal-expired event closes it"
bound = false

[[acceptance]]
text = "Given an expired proposal whose tracker event is read again, when recorded, then it stays closed"
bound = false
+++

Implements mirror.md section 3.5 (expiry).

Proposals expire after [mirror] proposal_ttl_days (default 30) as proposal-expired events written by the run; an expired proposal is never reopened by a re-read.
