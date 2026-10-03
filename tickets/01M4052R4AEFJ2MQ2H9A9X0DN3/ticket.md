+++
id = "01M4052R4AEFJ2MQ2H9A9X0DN3"
title = "GitHub schema validation and the repository inventory of managed labels, milestones and issue types"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-03T05:51:35Z"
idempotency_key = "m2-mirror2-gh-schema-inventory"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/github/schema.rs", "crates/frob-mirror/src/inventory.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[links]]
kind = "blocked-by"
target = "01M3ZX83E71BKE3PHY83G2NT7K"

[[acceptance]]
text = "Given a mapping naming a missing label, when the run starts, then it fails once with one diagnostic and a remedy before any write"
bound = false

[[acceptance]]
text = "Given a repository-level label rename since the last inventory, when the inventory is read, then the change is recorded once with fidelity gap"
bound = false

[[acceptance]]
text = "Given a project field other than status, when reconciled, then it is read and never written"
bound = false
+++

Implements mirror.md sections 3.4 (repository-level inventory) and 3.6 (managed labels and types exist; project fields).

Validate the mapping against the repository's labels, issue types and states before any write; keep an inventory of managed labels, milestones and issue types so a repository-level rename is caught once, not per issue. Project fields other than status are read-time only.
