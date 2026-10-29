+++
id = "01M62VRJMEEJK8EZCM0RV29FE6"
title = "JS coverage: detect runner declared in workspace member package.json"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-29T03:37:51Z"
updated = "2026-10-29T07:23:51Z"
scope = ["crates/frob-evidence/src/coverage/js.rs", "crates/frob-evidence/tests/**", "docs/design/testing.md"]

[[acceptance]]
text = "Given a workspace whose root package.json lacks a test runner but a member package.json declares vitest or jest, when coverage detection runs, then the JS runner is detected; a repo with no runner anywhere is still reported as not run"
bound = true
+++

found while working ~1X6RRD6: has_tests reads only the root package.json, so monorepo members are missed.
