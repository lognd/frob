+++
id = "01M62VRJMEEJK8EZCM0RV29FE6"
title = "JS coverage: detect runner declared in workspace member package.json"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-29T03:37:51Z"
updated = "2026-10-29T06:45:56Z"
scope = ["crates/frob-evidence/src/coverage/js.rs", "crates/frob-evidence/tests/**"]

[[acceptance]]
text = "Given a workspace whose root package.json lacks a test runner but a member package.json declares vitest or jest, when coverage detection runs, then the JS runner is detected; a repo with no runner anywhere is still reported as not run"
bound = true
+++

found while working ~1X6RRD6: has_tests reads only the root package.json, so monorepo members are missed.
