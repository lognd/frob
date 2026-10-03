+++
id = "01M3ZX83XX6D2N7XDTVRVYV6TS"
title = "GitHub adapter writes: create, update, close with reason, sub-issues or body links"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T05:51:57Z"
idempotency_key = "m2-mirror-gh-write"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/github/write.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83E71BKE3PHY83G2NT7K"

[[links]]
kind = "blocked-by"
target = "01M3ZX83NZ4PAM53VQCHXPE1R8"

[[links]]
kind = "blocked-by"
target = "01M3ZX83T22GTC94BW4PM742G1"

[[acceptance]]
text = "Given a dropped ticket, when published, then the issue is closed with the reason and not deleted"
bound = false

[[acceptance]]
text = "Given an issue deleted in the tracker, when the next run publishes, then it is recreated and the recreation is reported"
bound = false
+++

Implements mirror.md sections 2 and 3 (deletions and drops).

Never delete in the tracker: a dropped ticket is closed with its reason and a deleted issue is recreated and reported; relations use native links where available else body links.
