+++
id = "01M4H6C8C673JAX10ZMJD1T9DP"
title = "Bulk event reads cost 215 us per blob: ticket doctor 1.3 s and cycle velocity 1.06 s stay above 0.5 s"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T20:41:20Z"
updated = "2026-10-09T20:41:20Z"
labels = ["area:pm"]
scope = ["crates/gob-git/src/read.rs", "crates/frob-ledger/src/ledger.rs"]

[[acceptance]]
text = "Given ticket doctor and cycle velocity on this repository in a profiling build, when timed, then each is under 0.5 s"
bound = false
+++

Found while working ~807V4XM. After the bulk reads, cycle velocity spends 0.86 s of 1.06 s in read_events_many_at over 4004 event files (one gix find_blob plus a toml parse each, no object cache or parallelism). Options: a pack/object cache in gob-git, parallel blob reads, or caching parsed done-transition facts in the index.
