+++
id = "01M4X64ATCQ55PKCTX0HEVH0W5"
title = "frob test: Argument list too long (E2BIG) on full-workspace base run"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "Claude"
created = "2026-10-14T12:27:54Z"
updated = "2026-10-14T13:07:49Z"
scope = ["crates/frob-test/**", "crates/frob-tests/**"]

[[acceptance]]
text = "Given a full-workspace run, when frob test --base experimental runs, then no spawn fails with E2BIG"
bound = true
+++

frob test --base experimental fails with E-INTERNAL failed to spawn child: Argument list too long. Pass package/test filters via file or chunk them.
