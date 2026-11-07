+++
id = "01M6TDDRPSHJSBXGE6P5N6V4TP"
title = "Fix verb_table_drift: add agent install/hook/heavy/profile to grimble-ci VERBS"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-07T07:09:04Z"
updated = "2026-11-07T07:18:29Z"
labels = ["no-story"]
scope = ["crates/grimble-ci/src/**"]

[[acceptance]]
text = "Given the real clap tree, when verb_table_drift runs, then both drift tests pass"
bound = true
+++

crates/grimble-ci/src/verbs.rs VERBS lacks agent install, hook, heavy and profile; two frob-cli it verb_table_drift tests fail.
