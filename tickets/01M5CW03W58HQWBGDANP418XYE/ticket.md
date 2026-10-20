+++
id = "01M5CW03W58HQWBGDANP418XYE"
title = "Fresh clones and CI get a local frob-tickets branch"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T15:05:49Z"
idempotency_key = "dt-DT02"
scope = ["crates/frob-ledger/src/branch.rs", "crates/frob-ledger/tests/branch.rs", "crates/frob/src/init.rs", "crates/frob/src/ticket/branch_cmd.rs", "crates/frob/src/ticket/doctor_cmd.rs", "crates/frob/tests/it/ticket_branch.rs", "crates/gob-git/src/fallback.rs", "crates/gob-git/src/ledger.rs", "crates/gob-git/src/spawn.rs"]

[[acceptance]]
text = "ticket branch init adopts origin's frob-tickets instead of refusing, including a shallow single-branch clone"
bound = true

[[acceptance]]
text = "frob init in orphan mode creates the local ticket branch from origin"
bound = true

[[acceptance]]
text = "ticket doctor --fix creates the missing ticket branch and plain doctor refuses with E-DOCTOR-TICKET-BRANCH-MISSING"
bound = true
+++

init and doctor --fix create it from origin instead of refusing; shallow clones handled. See docs/design/distributed-tickets.md.
