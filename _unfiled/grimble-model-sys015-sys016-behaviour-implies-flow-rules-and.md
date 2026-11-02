+++
id = "01M6CKH5T88K0H44GH91F0PXRG"
title = "grimble-model: SYS015/SYS016 behaviour-implies-flow rules and CLAIM003 unresolved verdicts"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-01T22:26:25Z"
updated = "2026-11-02T03:27:04Z"
scope = ["crates/grimble-model/src/claim.rs,crates/grimble-model/src/plan_check.rs,crates/grimble-model/src/rules/**,crates/grimble-model/tests/corpus/**", "crates/grimble-model/src/claim.rs", "crates/grimble-model/src/plan_check.rs"]

[[links]]
kind = "blocked-by"
target = "01M6CFZKEKAJM0YF9FB5820W3Y"

[[links]]
kind = "blocked-by"
target = "01M6CFZKPGPCAE9565S7KVZE90"

[[acceptance]]
text = "SYS/CLAIM share of notes/research/grmb-corpus mockups d01..d11 and stress files: findings match documented ones; needs ~5820W3Y and ~7KVZE90"
bound = false
+++

Split from ~5820W3Y (parse-only). Implements SYS flow and CLAIM003 findings documented in the d01..d11 mockup headers, spec docs/design/grmb-spec.md (13.5). Also see ~7KVZE90 (D157 membership).
