+++
id = "01M4069Z4MQBBH3Q938Y3S3WBF"
title = "Exit: binaries and wheel install on the five targets with artifact smoke"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-05T05:14:26Z"
idempotency_key = "m2-rel-accept-install"
labels = ["milestone:2", "area:release"]
scope = [".github/workflows/release.yml", "crates/frob-release/tests/release_workflow.rs", "docs/guides/release.md", "docs/design/releases.md"]

[[links]]
kind = "blocked-by"
target = "01M4069Y1YR0XCN4BKDDH63PV1"

[[links]]
kind = "blocked-by"
target = "01M4069YQHN3EMTKR3RNE8Z036"

[[links]]
kind = "blocked-by"
target = "01M450VBPVEBZQZ5ANM1T8TCTA"

[[acceptance]]
text = "Given the rc run, when artifacts install on each target, then frob doctor and frob check succeed except exempt targets, each exempt target listed with its reason"
bound = true

[[acceptance]]
text = "Given the rc run, when read, then no job exceeded its timeout"
bound = true
+++

Exit criterion 1 of milestone 0.532.0. A dry-run release (workflow_dispatch on a pre-release tag such as frob-v0.532.0-rc.1, publishing nowhere) builds and smokes all five targets; evidence is the run URL recorded as an evidence note on this ticket; the exemption list is the documented one.
