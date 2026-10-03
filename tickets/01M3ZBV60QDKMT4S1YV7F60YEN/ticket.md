+++
id = "01M3ZBV60QDKMT4S1YV7F60YEN"
title = "G06 follow-ups: one RequiredReason, one Polarity, rule pages show polarity, TICK002 must_measure"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T22:30:33Z"
updated = "2026-10-02T23:10:37Z"
idempotency_key = "m2-g06-followups"
labels = ["milestone:2"]
scope = ["crates/gob-diagnostics/**", "crates/gob-check/**", "crates/gob-ir/**", "crates/gob-dev/**", "crates/frob-ledger/**", "docs/reference/**", "docs/schemas/**", "crates/frob-check/**"]

[[acceptance]]
text = "Given the workspace, when grepped for RequiredMarks and for a Polarity enum outside gob-rules, then neither exists and every rule page shows polarity"
bound = true
+++

From ~KKR84AW: gob-diagnostics re-exports gob_rules::RequiredReason and drops RequiredMarks so the gate reads Finding.required directly (then delete gate_reason in gob-check required.rs); gob-ir replaces its Polarity with pub use gob_rules::Polarity; gob-dev renders polarity and must_measure on rule pages and the generated docs are regenerated; frob-ledger sets must_measure on TICK002.
