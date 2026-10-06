+++
id = "01M48Q4F93B4RKTCW1E59MXB7Z"
title = "Adapter-less text is Unresolved (reason fidelity, rolled up) for capability rules, NotApplicable only for binaries and featureless languages"
type = "bug"
category = "todo"
priority = "high"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:41:01Z"
updated = "2026-10-06T23:25:21Z"
scope = ["crates/gob-check/**", "crates/frob-check/**", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M48R00MZS92F2KY5T60SBHYV"

[[acceptance]]
text = "an adapter-less text file gives one rolled-up Unresolved per capability rule and language"
bound = false

[[acceptance]]
text = "a binary file stays NotApplicable"
bound = false

[[acceptance]]
text = "frob check on this repository stays without errors and the rolled-up counts are listed"
bound = false
+++

Decision D106: universal-model.md 3.3 and 6 say an artifact with no adapter is Unresolved; gob-check status.rs and docs/reference/fidelity.md make it NotApplicable for capability rules, a silent pass. Change subject_status_for so adapter-less text yields one rolled-up Unresolved per rule and language with reason fidelity, keep NotApplicable for binaries and declared NotApplicable capability cells, and update fidelity.md and frob-check/tests/fidelity.rs. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
