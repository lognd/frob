+++
id = "01M4P4VHMW4AMB5R800DJ5WB66"
title = "build: fastest linker plus dynamic dev/test profile, static release profile; keep only if measured savings"
type = "task"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-11T18:50:57Z"
updated = "2026-10-28T12:55:51Z"
labels = ["no-story"]
scope = ["Cargo.toml,.cargo/**,docs/**,crates/gob-dev/**"]

[[acceptance]]
text = "baseline and after timings (one-line change in gob-text: link phase, frob test, frob land, disk footprint of target) are recorded in the ticket with the commands used"
bound = false

[[acceptance]]
text = "a dev/test profile uses the fastest available linker and prefer-dynamic shared libraries; release binaries build fully static with the default profile and are unchanged in behavior"
bound = false

[[acceptance]]
text = "the change is kept only if the measured saving is significant (at least 30% off link or test-build wall time or 30% off target disk); otherwise reverted and the numbers documented"
bound = false
+++

no-story: internal engineering task in Cargo.toml,.cargo/**,docs/**,crates/gob-dev/**; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
