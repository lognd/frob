+++
id = "01M4CTTZGDBKBNQ0CTEYYJGRFJ"
title = "Definition of done per ticket type: epics and docs tickets are not asked for a changelog fragment or measured evidence by default"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:42Z"
updated = "2026-10-22T01:16:48Z"
scope = ["changelog.d/**", "crates/frob-pm/**", "crates/frob-ledger/**", "crates/frob-release/**", "crates/frob-evidence/Cargo.toml", "crates/frob-evidence/src", "crates/frob-evidence/tests"]

[[acceptance]]
text = "Given an epic whose children are done, when it closes, then no changelog fragment or command evidence is required by default"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md MEDIUM.
