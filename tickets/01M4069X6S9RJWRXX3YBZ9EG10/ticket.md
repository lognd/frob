+++
id = "01M4069X6S9RJWRXX3YBZ9EG10"
title = "frob release cut VERSION: bump, compile CHANGELOG, one commit through land, tag"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T08:26:16Z"
idempotency_key = "m2-rel-release-cut"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/cut.rs", "crates/frob-land/src/**", "crates/frob/src/release_cmd.rs", "crates/gob-git/src/**", "crates/frob-pm/src/event.rs", "crates/frob-pm/src/fold.rs", "crates/frob-release/Cargo.toml", "crates/frob-release/src/lib.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069W8ECWEPBH6YPAR7X0X0"

[[links]]
kind = "blocked-by"
target = "01M4069WSTV5ZJMRPYR2YECX6Q"

[[links]]
kind = "blocked-by"
target = "01M4069X2KPQ6RNV26SWSY4VA5"

[[acceptance]]
text = "Given a ready milestone, when release cut runs, then one commit holds the bump and CHANGELOG, fragments are gone and tag frob-vVERSION points at it"
bound = false

[[acceptance]]
text = "Given status not ready, when cut runs without --override, then it exits 3 with the remedy"
bound = false
+++

Requires status ready or `--override --reason` (recorded as a ledger event); bump, compile CHANGELOG.md and remove fragments, commit on the base branch through the land machinery (CAS, one commit), tag frob-vVERSION (annotated, local; push is opt-in), and record the cut (version, commit, tag oid) as a ledger event that REL001 reads. Refuses a dirty tree and an existing tag.
