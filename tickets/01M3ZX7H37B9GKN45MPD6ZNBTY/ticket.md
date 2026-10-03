+++
id = "01M3ZX7H37B9GKN45MPD6ZNBTY"
title = "frob check runs rule test for std and repository packs"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:23Z"
updated = "2026-10-03T03:34:23Z"
idempotency_key = "m2-grl-check-integration"
labels = ["milestone:2", "area:grl"]
scope = ["crates/frob-check/src/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FCFBJSWMTZGCQMW7215"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[acceptance]]
text = "Given a repository pack whose example no longer matches, when frob check runs, then a GRL016 finding names the rule and example"
bound = false

[[acceptance]]
text = "Given all examples passing, when frob check runs, then no GRL finding is emitted and the run reports the example counts"
bound = false
+++

Implements grl-spec.md section 9 (last bullet).

A failing embedded example or a GRL compile error in a std or repository pack is a check finding, so rules never rot.
