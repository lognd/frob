+++
id = "01M5GVVBYCPX09T4N4E0HV9K7N"
title = "frob-release dev_workflow test treats the docs-only job as a test job the dev channel must await"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T03:53:03Z"
updated = "2026-10-22T03:53:06Z"
scope = ["crates/frob-release/tests/it/dev_workflow.rs"]

[[acceptance]]
text = "frob-release dev_workflow workflow test passes against the current ci.yml"
bound = false
+++

dev-artifacts and dev-publish need every always-run test job; the path-scoped docs-only job is skipped on code pushes (and a skipped need skips its dependants) so it joins crunk and crunk-node as a scoped job
