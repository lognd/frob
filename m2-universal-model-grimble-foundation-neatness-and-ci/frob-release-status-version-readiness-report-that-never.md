+++
id = "01M4069WSTV5ZJMRPYR2YECX6Q"
title = "frob release status [VERSION]: readiness report that never fails"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T15:28:22Z"
idempotency_key = "m2-rel-release-status"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-release/src/status.rs", "crates/frob/src/release_cmd.rs", "crates/frob-release/Cargo.toml", "crates/frob-pm/src/rules/membership.rs", "crates/frob-release/src/lib.rs", "crates/frob/tests/release_status.rs", "Cargo.lock", "docs/reference/**", "crates/frob-release/src/error.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069RACAQ8Z2C8APK0YKGNK"

[[links]]
kind = "blocked-by"
target = "01M4069RJJ4C73Z6GKKSV1E7PS"

[[links]]
kind = "blocked-by"
target = "01M4069W8ECWEPBH6YPAR7X0X0"

[[acceptance]]
text = "Given a milestone with an unevidenced criterion, when release status runs, then it lists it and exits 0"
bound = true

[[acceptance]]
text = "Given everything ready, when release status runs, then it prints ready and the changelog preview"
bound = true
+++

Reports: every exit criterion evidenced; no open ticket in the milestone's epics (or labelled release:VERSION before the object exists); fragments compile; the changelog preview; what is left. Exit 0 always. CI-green-on-tip and the forecast are separate tickets; GEN001 is reported when it exists and the pack lock when packs ship.
