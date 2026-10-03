+++
id = "01M418CX3WCN4WPW7XTZ2QPBZ2"
title = "Extract a reusable workflow_call for plan, build and smoke, used by release.yml and dev.yml"
type = "task"
category = "in-progress"
priority = "low"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T16:08:48Z"
updated = "2026-10-03T18:50:32Z"
labels = ["area:release"]
scope = [".github/workflows/release.yml", ".github/workflows/dev.yml", "crates/frob-release/tests/release_workflow.rs", "crates/frob-release/tests/dev_workflow.rs", ".github/workflows/build-smoke.yml", "docs/design/releases.md", "packaging/pypi/BUILDING.md", "frob.lock"]

[[acceptance]]
text = "Given release.yml and dev.yml, when either runs, then plan, build and smoke come from one reusable workflow_call workflow"
bound = false

[[acceptance]]
text = "Given the release workflow tests, when they run after the extraction, then they pass unchanged in meaning"
bound = false
+++

found while working ~NE8Z036: dev.yml duplicates release.yml's build matrix, pinned dist install, and archive smoke; dev_workflow.rs pins equality as a drift guard. Extract plan, build and smoke into one workflow_call workflow called by both, keeping release.yml behaviour and its tests green, and drop the duplicate matrix and the equality test.
