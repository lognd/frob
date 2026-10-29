+++
id = "01M62VRJMEEJK8EZCM0RV29FE6"
title = "JS coverage: detect runner declared in workspace member package.json"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T03:37:51Z"
updated = "2026-10-29T03:37:51Z"
scope = ["crates/frob-evidence/src/coverage/js.rs"]
+++

found while working ~1X6RRD6: has_tests reads only the root package.json, so monorepo members are missed.
