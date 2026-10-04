+++
id = "01M42MGP62EPY4K7C29M0388X5"
title = "One corrupt lease file blocks lease list and frob work for the whole clone"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-04T04:59:49Z"
updated = "2026-10-04T13:39:12Z"
scope = ["crates/frob-lease/**", "crates/frob/src/doctor.rs", "crates/frob/tests/gc.rs", "crates/frob/tests/snapshots/cli__doctor_fresh_repo.snap", "crates/frob/tests/snapshots/cli__doctor_schema.snap", "docs/design/cli.md"]

[[acceptance]]
text = "Given a corrupt lease file, when lease list and work run, then they proceed and report the corrupt file"
bound = true
+++

Reproduced. Skip and report a corrupt lease (doctor can quarantine it); never let one bad file block every verb. Evidence and repro: notes/review/v1-gap/D-incidents.md (probe list).
