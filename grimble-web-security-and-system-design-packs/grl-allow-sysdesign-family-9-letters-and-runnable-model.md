+++
id = "01M5F1EZSNXY1H1S3CP8AJJH4Q"
title = "GRL: allow SYSDESIGN family (9 letters) and runnable model example input"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-21T10:52:40Z"
updated = "2026-10-21T11:13:26Z"
labels = ["grimble-packs"]
scope = ["crates/gob-rules/src/id.rs", "crates/gob-plan/**", "changelog.d/01M5F1EZSNXY1H1S3CP8AJJH4Q.*", "Cargo.lock", "docs/design/rules.md", "docs/design/grl-spec.md", "docs/reference/grl/**"]

[[acceptance]]
text = "RuleId accepts SYSDESIGN101 (family up to 9+ letters) and plan validation agrees"
bound = true

[[acceptance]]
text = "grimble rule test runs example inputs of kind model so lang - rules over model.nodes have fire/clean examples"
bound = true
+++
