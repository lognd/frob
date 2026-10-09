+++
id = "01M4DPJG0W39SCKZE5N807V4XM"
title = "frob-ledger: event blobs per ticket from one snapshot walk (no per-ticket tip:dir rev_parse)"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T12:07:24Z"
updated = "2026-10-09T20:22:47Z"
scope = ["changelog.d/**", "crates/frob-ledger/src/ledger.rs", "crates/frob-ledger/src/doctor.rs", "crates/frob-ledger/tests/ledger.rs", "crates/frob-pm/src/cycle/velocity.rs"]

[[acceptance]]
text = "Given ticket doctor and cycle velocity on this repository in a release build, when timed, then each is under 0.5 s and rev_parse runs once per command (counter test)"
bound = false
+++

Follow-up from ~VXFAY3P: read_events_at still resolves tip:dir per ticket; most of the remaining ticket doctor (1.3-4.2 s) and cycle velocity (0.85 s) cost.
