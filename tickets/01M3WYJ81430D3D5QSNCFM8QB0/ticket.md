+++
id = "01M3WYJ81430D3D5QSNCFM8QB0"
title = "frob-ledger: first-class evidence, evidence-bypass and land events with an append API"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-03T06:35:21Z"
aliases = ["T-0036"]
labels = ["milestone:2.0.0", "component:frob-ledger", "release:0.532.0"]
scope = ["crates/frob-ledger/**", "crates/frob-evidence/src/**", "crates/frob-land/src/**"]

[[acceptance]]
text = "Given an evidence event with accepts, when the ticket is folded, then the matching acceptance items are bound"
bound = false

[[acceptance]]
text = "Given frob-evidence and frob-land, when grepped for commit_paths, then neither calls it directly"
bound = false
+++

frob-evidence and frob-land each copy a private commit helper to write event files and re-fold ticket.md because EventBody has no Evidence, EvidenceBypass or Land variants and commit_events is pub(crate). Add the variants (fold binds acceptance[].bound from evidence accepts; land records base ref, commit oid, pushed), a public Ledger::append(ticket, EventBody) that writes, re-folds and commits on the ledger ref, and switch frob-evidence and frob-land to it, deleting the copies.
