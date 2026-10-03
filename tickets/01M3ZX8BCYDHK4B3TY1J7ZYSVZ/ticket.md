+++
id = "01M3ZX8BCYDHK4B3TY1J7ZYSVZ"
title = "Mirror: reconcile tracker edits deterministically instead of blocking (MIR002 redefined)"
type = "docs"
category = "todo"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:34:50Z"
updated = "2026-10-03T03:34:50Z"
idempotency_key = "m2-mirror-reconcile"
labels = ["milestone:2", "area:mirror"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given mirror.md and security.md, when read, then no tracker edit can fail any check or block a land, every reverted edit is captured as a proposal, convergence and the race case are specified, and security.md section 5 records the decisions"
bound = false
+++

Owner decision 2026-10-04: an edit made in the tracker must never block anything; detection is easy, so handling must be deterministic. Replace skip-and-block with reconcile: per-field single ownership (repository-owned fields are reverted to the ledger's projection; tracker-owned fields are never written), every reverted edit is captured from the tracker's change history as a proposal event on the ticket so nothing is lost, even when an edit races the mirror's write; MIR002 becomes an Advisory note; proposals are listed and accepted or declined with ticket verbs. Also record security.md section 5: escaping option A decided; the owner performs the one-time trust step; the trust review UX is pending a second audit (notes/review/trust-ux-audit.md).
