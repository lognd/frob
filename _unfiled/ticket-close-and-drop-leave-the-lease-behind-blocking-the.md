+++
id = "01M42MGN8882Y65TVXH0V1WTNR"
title = "ticket close and drop leave the lease behind, blocking the next work on overlapping scope"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T04:59:48Z"
updated = "2026-10-04T12:17:34Z"
scope = ["crates/frob/src/ticket/**", "crates/frob/tests/terminal_lease.rs"]

[[acceptance]]
text = "Given a leased ticket, when it is closed or dropped, then its lease is released and an overlapping work succeeds"
bound = true
+++

Reproduced: close leaves the lease (contradicts the design: leases release on every terminal transition). Release on close and drop, and reap leases of terminal tickets. Evidence and repro: notes/review/v1-gap/D-incidents.md (P-03).
