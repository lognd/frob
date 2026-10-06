+++
id = "01M47QV17V1KZ6K50C7H77MRSP"
title = "Snapshot hygiene step: unreferenced and pending snapshots fail cargo dev ci"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:06Z"
updated = "2026-10-06T08:50:52Z"
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml"]

[[acceptance]]
text = "a stray .snap.new or unreferenced .snap fails the snapshots step"
bound = true

[[acceptance]]
text = "ci.yml runs the step through cargo dev ci and the parity test passes"
bound = true
+++

build-test-ci.md section 6 (cargo insta test --unreferenced reject). The nextest step runs with INSTA_UPDATE=no; a snapshots step in crates/gob-dev/src/ci.rs fails on any .snap.new or pending-snap file and on snapshot files no test references.
