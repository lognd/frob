+++
id = "01M6A2TC5VJ4475NDA1SEAXXYV"
title = "Register PLAN rule family owner (grimble-bind) in family_owners test"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T22:55:51Z"
updated = "2026-10-31T22:55:57Z"
idempotency_key = "plan-family-owner-row"
scope = ["crates/gob-rules/tests/family_owners.rs"]

[[acceptance]]
text = "every_rule_family_has_exactly_one_owning_crate passes with PLAN owned by grimble-bind"
bound = false
+++

PLAN family (A1A7YMH/WR05MGF/M7YR6SS) was added without an OWNERS row; nextest fails.
