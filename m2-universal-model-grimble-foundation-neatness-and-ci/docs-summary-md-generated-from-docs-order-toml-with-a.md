+++
id = "01M3ZX877WJ3150E735XCH7F2D"
title = "docs/SUMMARY.md generated from docs/order.toml with a coverage check"
type = "task"
category = "done"
outcome = "duplicate"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-09T20:45:26Z"
idempotency_key = "m2-nav-summary"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/gob-dev/src/render/summary.rs", "docs/order.toml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85N2KZ39PG65MX0YT2P0"

[[acceptance]]
text = "Given a docs page absent from SUMMARY.md and not excluded, when `cargo dev gen all --check` runs, then GEN001 reports it"
bound = false

[[acceptance]]
text = "Given docs/order.toml, when generated, then SUMMARY.md follows its order and lists reference pages from the generators"
bound = false
+++

Implements navigation.md section 3.2.

Hand-written order file; reference sections are generated lists; every docs/**/*.md must appear in SUMMARY.md or be explicitly excluded.
