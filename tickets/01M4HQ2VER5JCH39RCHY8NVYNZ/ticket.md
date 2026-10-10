+++
id = "01M4HQ2VER5JCH39RCHY8NVYNZ"
title = "ticket doctor reports 131 pre-existing E-DOCTOR-ORDER issues on this repository; repair them (doctor --fix or a reconcile) before the ledger cut-over"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-10T01:33:18Z"
updated = "2026-10-10T02:26:31Z"
scope = ["crates/frob-ledger/src/doctor.rs", "changelog.d/**"]

[[acceptance]]
text = "Given this repository's ledger, when frob ticket doctor runs, then it reports zero E-DOCTOR-ORDER issues (repaired by a documented reconcile, events never rewritten)"
bound = true
+++

Found during the ~128J4NT scratch-clone migration: 131 order issues before and after; makes the cut-over's 'doctor shows no errors' check impossible.
