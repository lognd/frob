+++
id = "01M4D6NE2VCV26EG54JD672RXD"
title = "frob-ledger: sync the ticket index incrementally by tree diff, keyed by tree id; pm writes update the key"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:24Z"
updated = "2026-10-08T09:43:13Z"
scope = ["changelog.d/**", "crates/frob-ledger/**", "crates/frob-pm/**"]

[[acceptance]]
text = "Given a pm write followed by a ticket read, when timed, then the read does no full rebuild (counter test) and cycle plan --apply rebuilds at most once"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 2: Ledger::synced (ledger.rs:666) rebuilds all tickets after any non-ticket write; cycle plan --apply 7.4 s, assign 1.3 s, milestone add 1.1 s, release cut 2.9 s.
