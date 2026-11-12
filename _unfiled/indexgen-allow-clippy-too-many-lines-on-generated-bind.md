+++
id = "01M778EENHT3NQ80WZRG76M9WS"
title = "indexgen: allow clippy::too_many_lines on generated bind()"
type = "task"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-12T06:52:11Z"
updated = "2026-11-12T11:09:35Z"
scope = ["crates/gob-rules/src/indexgen.rs", "crates/crunk-rules/src/rules/mod.rs", "crates/frob-ack/src/rules/mod.rs", "crates/frob-lease/src/rules/mod.rs", "crates/frob-ledger/src/rules/mod.rs", "crates/frob-obligations/src/rules/mod.rs", "crates/frob-pm/src/rules/mod.rs", "crates/frob-release/src/rules/mod.rs", "crates/frob-tests/src/rules/mod.rs", "crates/gob-check/tests/product_rules/alpha/src/rules/mod.rs", "crates/gob-check/tests/product_rules/beta/src/rules/mod.rs"]

[[acceptance]]
text = "Given a rule crate with enough rules that generated bind() exceeds 100 lines, when clippy runs, then the generated bind() carries an allow of clippy::too_many_lines with a reason and raises no LINT001"
bound = false
+++

found while working ~WM2DDBN: crunk-rules bind() is now 101 lines and trips clippy::too_many_lines; generated mod.rs cannot carry a hand allow
