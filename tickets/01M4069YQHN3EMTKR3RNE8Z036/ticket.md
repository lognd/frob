+++
id = "01M4069YQHN3EMTKR3RNE8Z036"
title = "Dev channel: every green land builds artifacts to a GitHub prerelease dev"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-03T16:12:08Z"
idempotency_key = "m2-rel-dev-channel"
labels = ["milestone:2", "area:release"]
scope = [".github/workflows/dev.yml", ".github/workflows/ci.yml", "crates/frob-release/tests/dev_workflow.rs", "docs/design/releases.md"]

[[links]]
kind = "blocked-by"
target = "01M4069XFWGEFARNVXTXHT82FS"

[[acceptance]]
text = "Given a green CI run on the base branch, when dev.yml runs, then the dev prerelease holds fresh archives naming the sha"
bound = true

[[acceptance]]
text = "Given a failed CI run, when dev.yml triggers, then it does nothing"
bound = true
+++

workflow_run (CI success on the base branch) rebuilds the cargo-dist archives and replaces assets on the prerelease tagged dev with the tested sha in the body; contents: write only on the publishing job, never secrets from forks, nothing published to registries, timeouts on all jobs. This repository's tip is branch experimental until main is cut; the trigger branch list is one knob in the workflow env.
