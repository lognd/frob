+++
id = "01M4052R88Y0A9HQHDB86ERMEM"
title = "GitHub adapter writes: update, close with reason, additive label endpoints, sub-issues or body links"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-03T05:51:35Z"
idempotency_key = "m2-mirror2-gh-writes"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/github/write.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[links]]
kind = "blocked-by"
target = "01M3ZX83E71BKE3PHY83G2NT7K"

[[links]]
kind = "blocked-by"
target = "01M3ZX83T22GTC94BW4PM742G1"

[[links]]
kind = "blocked-by"
target = "01M4052QNSFSWV0SQ0A05XQ12K"

[[acceptance]]
text = "Given a changed label set, when published, then only add-label and remove-label calls for frob: labels are made and a tracker-owned label survives"
bound = false

[[acceptance]]
text = "Given a dropped ticket, when published, then the issue is closed with the reason and never deleted"
bound = false

[[acceptance]]
text = "Given two mutations in one run and a fake clock, when sent, then at least one second separates them"
bound = false

[[acceptance]]
text = "Given a write that fails with 5xx, when recorded, then it is marked failed with no effect assumed and retried next run"
bound = false
+++

Implements mirror.md sections 3.2 (serial writes, one second apart), 3.3 (never recreate) and 3.4 (additive endpoints).

Update and close with reason; labels and assignees change only through add and remove endpoints for the frob: namespace, never by replacing the set, so tracker-owned labels survive; relations use native sub-issues or links where the capabilities say so, else body links. Never delete in the tracker; a dropped ticket is closed with its reason. Create is the create-protocol ticket.
