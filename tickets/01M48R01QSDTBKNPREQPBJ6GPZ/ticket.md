+++
id = "01M48R01QSDTBKNPREQPBJ6GPZ"
title = "Generated per-crate rule index and product_rules! with compile-time uniqueness"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:05Z"
updated = "2026-10-07T00:28:01Z"
scope = ["crates/gob-rules/**", "crates/gob-check/**", "crates/gob-dev/**", "crates/frob-check/src/**", "crates/grimble-check/src/**", "crates/crunk-check/src/**", "docs/design/rule-authoring.md"]

[[links]]
kind = "blocked-by"
target = "01M48R016FCW4AR269QN88H9SY"

[[acceptance]]
text = "removing a crate from product_rules! while keeping the dependency fails cargo check"
bound = false

[[acceptance]]
text = "a duplicate id across two crates of a product fails to compile naming both"
bound = false

[[acceptance]]
text = "cargo dev gen --check covers rules-index"
bound = false

[[acceptance]]
text = "gob-dev has no rule link anchor"
bound = false
+++

M4: cargo dev gen rules-index writes each rule crate's src/rules/mod.rs (mods, METAS, binding), GEN001 and a crate freshness test check it; product_rules! lists a product's rule crates in one line; const assert_unique over ids, slugs, renamed and retired ids per crate, per product and across products; deny(unused_crate_dependencies) in product crates; gob-dev lists products explicitly and loses the link anchor. Rescopes ~67J8R53 to rules. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
