+++
id = "01M4052TC4BVA3JFFCHZX82EWS"
title = "Per-issue reconcile: revert repository-owned fields changed by others and propose"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-reconcile"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/reconcile.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[links]]
kind = "blocked-by"
target = "01M4052RMBKXD6T8ANNFWJ751M"

[[links]]
kind = "blocked-by"
target = "01M4052SFS22HBR73HQN1E4FA4"

[[links]]
kind = "blocked-by"
target = "01M4052SKTA49WCV6AXJFCAM9J"

[[links]]
kind = "blocked-by"
target = "01M4052SQS2X5XYN24DE9ENQF8"

[[links]]
kind = "blocked-by"
target = "01M4052T420AX728KKZ2RDYSTX"

[[acceptance]]
text = "Given an issue whose title a human edited, when reconciled, then the title is reverted to the projection, one proposal is recorded, no check fails, and a second run changes nothing"
bound = false

[[acceptance]]
text = "Given a tracker-owned field edited by a human, when reconciled, then it is left unchanged"
bound = false

[[acceptance]]
text = "Given a bot-id history entry with no matching journaled write, when reconciled, then it is treated as an edit by unknown automation and reverted"
bound = false

[[acceptance]]
text = "Given an edit made between the mirror's read and its write, when the next run reads history, then the edit is recorded and nothing is lost"
bound = false
+++

Implements mirror.md section 3.4 (Per issue in a run; owner decision: never block).

Read the current values and the history after the cursor; for each repository-owned field changed by someone other than the mirror (including unknown automation), revert it to the projection and record the change as a proposal; never write a tracker-owned field. MIR002 is Advisory and never fails a check or a land.
