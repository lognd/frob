+++
id = "01M4BH0C9D5X79MFHTAYBHKQGE"
title = "Expired-lease recovery: land from the primary leases the primary; work refuses a resumed worktree"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-07T15:51:39Z"
updated = "2026-10-07T15:54:57Z"
idempotency_key = "lease-expired-recovery-gaps"
labels = ["milestone:2"]
scope = ["crates/frob-lease/**", "crates/frob-land/**", "crates/frob-worktree/**", "docs/design/tickets.md"]

[[acceptance]]
text = "Given a ticket whose lease expired with no overlapping lease since, when land runs from the primary root, then it renews the lease for the ticket's own worktree (not the primary) and lands"
bound = true

[[acceptance]]
text = "Given an in-progress ticket with no live lease, when frob work runs from that ticket's existing worktree, then it re-leases there instead of refusing E-TICKET-NOT-WORKABLE"
bound = true
+++

Measured 2026-10-07 after ~G2Y8E0R landed. (1) ~5N48KNK's lease expired while its agent was down; frob land ~5N48KNK from the primary root acquired a fresh lease whose holder worktree was the primary, then refused E-LAND-WRONG-WORKTREE (primary is on experimental); recovery needed work --steal from the ticket worktree. (2) ~GBBKJ6V: frob work from its own existing worktree refused E-TICKET-NOT-WORKABLE (in progress, no live lease); recovery needed requeue then work. Both should be the inferred-heartbeat path of D105: no manual recovery when nothing else took the scope. Never renew across a steal.
