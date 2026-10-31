+++
id = "01M69D74SAT6R0X0Q88YTCRAEM"
title = "grimble-bind: move the opaque error-set Unresolved from PLAN011 to PLAN041 on the waypoint"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T16:38:21Z"
updated = "2026-10-31T19:04:26Z"
idempotency_key = "grmb-cycle3-outcome-rule"
scope = ["crates/grimble-bind/**", "docs/reference/rules/**"]

[[acceptance]]
text = "plan_outcome_map reports the Unresolved for an Unknown waypoint error set under PLAN041 (required), anchored on the waypoint, as grmb-spec.md 16.2 and D185 say; PLAN011 keeps only the Advisory about a known failure no variant models"
bound = true

[[acceptance]]
text = "crates/grimble-bind/tests/outcome.rs asserts the rule id and anchor"
bound = true
+++

Follow-up of ~MHGA5VN cycle 3 M8: outcome.rs (26fe067d8e) landed with OUTCOME_RULE = PLAN011 on the impl anchor.
