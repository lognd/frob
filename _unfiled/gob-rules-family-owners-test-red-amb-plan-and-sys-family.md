+++
id = "01M6DQGH6Z3VB7CQTM9KF04V8N"
title = "gob-rules family_owners test red: AMB, PLAN and SYS family owners unregistered for grimble crates (found during ~3CCNEW9; ~SEAXXYV closed earlier)"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-11-02T08:55:12Z"
updated = "2026-11-02T08:59:22Z"
scope = ["crates/gob-rules/tests/family_owners.rs"]

[[acceptance]]
text = "every_rule_family_has_exactly_one_owning_crate passes: AMB owned by grimble-model, PLAN and SYS listed as split between grimble-bind and grimble-model"
bound = true
+++
