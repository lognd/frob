+++
id = "01M4052SKTA49WCV6AXJFCAM9J"
title = "Read-back normalization: compare after the tracker's own formatting"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-normalize"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/normalize.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[links]]
kind = "blocked-by"
target = "01M4052SFS22HBR73HQN1E4FA4"

[[acceptance]]
text = "Given a body the tracker reformats on write, when read back once and stored, then later runs see no difference and write nothing"
bound = false

[[acceptance]]
text = "Given a ledger change to the field, when published, then the new value is read back once again and stored"
bound = false

[[acceptance]]
text = "Given a write that does not stick when read back, when checked, then MIR001 is reported for that ticket with the reason write-not-sticking"
bound = false
+++

Implements mirror.md section 3.4 (MIR-AUD-20; assumption: writes stick when read back).

Values are compared after the tracker's own normalization, read back once after a write and stored in the shard, so the mirror does not rewrite fields the tracker reformats.
