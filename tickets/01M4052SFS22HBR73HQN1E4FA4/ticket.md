+++
id = "01M4052SFS22HBR73HQN1E4FA4"
title = "Field ownership: [mirror.fields], tracker_owned, never write a tracker-owned field"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-fields"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/fields.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83E71BKE3PHY83G2NT7K"

[[acceptance]]
text = "Given a projected field with no owner in [mirror.fields], when the config loads, then an error names the field"
bound = false

[[acceptance]]
text = "Given a field in tracker_owned or a label outside the frob: namespace, when writes are planned, then no operation writes it"
bound = false

[[acceptance]]
text = "Given a project field other than status, when planned, then it is read-only"
bound = false
+++

Implements mirror.md section 3.4 (One owner per field) and 3.6 (project status only).

Every projected field has exactly one owner in [mirror.fields] (materialized). In version 1 every field the mirror writes is repository-owned; tracker-owned are comments, reactions, labels outside the frob: namespace and fields in tracker_owned. A planned operation on a tracker-owned field is a programmer bug and cannot be expressed.
