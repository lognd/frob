+++
id = "01M3ZXGAN6AMYG9AKKTD77SN7W"
title = "Mirror reconcile: field ownership, revert repository-owned edits, converge"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:39:11Z"
updated = "2026-10-03T05:51:56Z"
idempotency_key = "m2-mirror-reconcile-engine"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83NZ4PAM53VQCHXPE1R8"

[[links]]
kind = "blocked-by"
target = "01M3ZX841SP0ZXM4CT18A4B8CV"

[[acceptance]]
text = "Given an issue whose title was edited in the tracker, when the mirror runs, then the title is reverted to the projection, no check fails, and a second run changes nothing"
bound = false

[[acceptance]]
text = "Given a tracker-owned field edited in the tracker, when the mirror runs, then it is left unchanged"
bound = false
+++

mirror.md 3.1. [mirror.fields] ownership table (materialized; v1 all written fields repository-owned; comments, reactions, non-frob: labels tracker-owned). Each run per issue: compare current state to the projection; revert repository-owned fields; never write tracker-owned ones; at most one host-template comment per issue per day. Idempotent and serialized (one writer). MIR002 tracker-edit-reverted as Advisory, never an error. Uses the adapter reads and writes.
