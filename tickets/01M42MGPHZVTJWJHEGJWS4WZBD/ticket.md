+++
id = "01M42MGPHZVTJWJHEGJWS4WZBD"
title = "frob check --fix writes non-atomically and without checking the file is unchanged since the check"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-04T04:59:50Z"
updated = "2026-10-04T13:12:29Z"
scope = ["crates/gob-check/src/**"]

[[acceptance]]
text = "Given a file edited between check and fix, when --fix runs, then it refuses that file; and an interrupted fix never leaves a partial file"
bound = false
+++

Found by reading source. Add one shared write_atomic; --fix checks the file digest first, re-parses the result and rolls back on failure. Evidence and repro: notes/review/v1-gap/D-incidents.md (P-02).
