+++
id = "01M4052WAB3H52W92NYG3AS571"
title = "Fake GitHub for replaying the model: history, listing, lost and late creates, rate limits"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-03T05:51:39Z"
idempotency_key = "m2-mirror2-fake-github"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/tests/support/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[acceptance]]
text = "Given a seed, when a scenario runs twice, then both runs are identical"
bound = false

[[acceptance]]
text = "Given a delayed create, when time advances, then the issue appears later with an event id in order"
bound = false

[[acceptance]]
text = "Given a call budget of B, when the B+1th call is made, then it is refused as rate-limited"
bound = false
+++

Implements the test support for mirror.md section 3.7 and docs/design/models/mirror/README.md section 2.

A deterministic fake tracker implementing the adapter trait: append-only history with event ids, listing by creator, read-your-writes lookup, adversaries (human edits of repository-owned and tracker-owned fields, marker spoof, human-created marked issue), network kinds (lost create, delayed create landing later, duplicated write), crashes injected at any step, rate-limit refusals counted per call.
