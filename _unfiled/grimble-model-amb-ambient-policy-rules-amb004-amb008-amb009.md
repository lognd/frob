+++
id = "01M6CKH5NBZR6KXAXQDSAVFSVM"
title = "grimble-model: AMB ambient-policy rules (AMB004, AMB008, AMB009) over parsed ambient/retry/fault items"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-01T22:26:24Z"
updated = "2026-11-02T02:44:12Z"
scope = ["crates/grimble-model/src/rules/**,crates/grimble-model/src/plan_check.rs,crates/grimble-model/tests/corpus/**", "crates/grimble-model/src/rules/**", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/tests/corpus/**", "docs/reference/rules/**", "docs/design/rules.md", "docs/README.md"]

[[links]]
kind = "blocked-by"
target = "01M6CFZKEKAJM0YF9FB5820W3Y"

[[links]]
kind = "blocked-by"
target = "01M6CFZKPGPCAE9565S7KVZE90"

[[acceptance]]
text = "AMB share of notes/research/grmb-corpus mockups d01..d11 and stress files: AMB findings match documented ones; needs ~5820W3Y and ~7KVZE90"
bound = true
+++

Split from ~5820W3Y (parse-only). Implements the AMB rule family documented in the d01..d11 mockup headers, spec docs/design/grmb-spec.md. Also see ~7KVZE90 (D157 membership).
