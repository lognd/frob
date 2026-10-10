+++
id = "01M4HTPMAS5TVK9S8Q47KD8R04"
title = "frob-pm doctor E-PM-ORDER uses the same symmetric clock-skew check that flagged normal command-clock lag in frob-ledger (~Y8NVYNZ); apply the same asymmetric order_skew rule"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-10T02:36:32Z"
updated = "2026-10-10T02:36:32Z"
scope = ["crates/frob-pm/src/doctor.rs", "changelog.d/**"]

[[acceptance]]
text = "Given a cycle or milestone event whose ULID was minted up to 6 hours after its at timestamp, when ticket doctor runs, then no E-PM-ORDER fires; an at ahead of its ULID by more than the skew still fires"
bound = false
+++

Follow-up noted by ~Y8NVYNZ's implementer.
