+++
id = "01M40T3WSDHBQ71K2F2FJT8C2Q"
title = "frob ack writes frob.lock on the ticket branch, then SCOPE001 flags it outside the lease"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:59:13Z"
updated = "2026-10-03T12:51:33Z"
idempotency_key = "m2-rel-locks-are-bookkeeping"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-check/**", "changelog.d/01M40T3WSDHBQ71K2F2FJT8C2Q.fixed.md"]

[[acceptance]]
text = "Given a ticket branch where frob ack changed frob.lock, when check --ticket runs, then frob.lock is not reported by SCOPE001"
bound = true
+++

Reported from the cloc repository (FROB_FEEDBACK.md item 4): frob ack (needed to attest frob:accept, EXC005) commits frob.lock on the ticket branch, and the next check --ticket reports SCOPE001 frob.lock is outside the scope lease, so every ticket that acks needs a manual scope widening. frob.lock and grimble.lock are bookkeeping written by frob's own verbs, like the ledger directory that SCOPE001 already exempts (~SF903MG): exempt them in branch_changes, while keeping drift rules on their content. Test: ack on a ticket branch, then check --ticket: no SCOPE001 for the lock.
