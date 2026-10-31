+++
id = "01M69AXEF0DZH0X55C8DJEDY70"
title = "PLAN006 error-set collection (owned by P4) and scenario plan.collected"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T15:58:06Z"
updated = "2026-10-31T20:25:15Z"
scope = ["crates/grimble-bind/**,crates/grimble-check/**", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/src/plan_index.rs", "docs/design/sibling-contract.md", "changelog.d/01M69AXEF0DZH0X55C8DJEDY70.changed.md", "crates/grimble-bind/**"]

[[acceptance]]
text = "Scenario plan.error_set and plan.collected reflect the collected step errors, not just fails_with."
bound = true
+++

Found while working ~ERF5VCQ; deferred from P2.
