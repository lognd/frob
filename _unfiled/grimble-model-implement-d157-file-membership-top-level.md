+++
id = "01M6CFZKPGPCAE9565S7KVZE90"
title = "grimble-model: implement D157 file membership (top-level planning items join the file's one system) in plan_check"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-01T21:24:23Z"
updated = "2026-11-02T02:15:57Z"
scope = ["crates/grimble-model/src/plan_check.rs", "crates/grimble-model/src/check.rs", "crates/grimble-model/tests/corpus/**"]
+++

found while working ~ZP5KR2Q. Every domain mockup (braced 'system s { }' with items at top level) reports MDL031 'outside any system'; plan_check.rs structure() only accepts name-prefix enclosure, not grmb-spec 11.2 membership rule 2.
