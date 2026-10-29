+++
id = "01M64WSNR41TCVNG5F8HH6N6BT"
title = "Generated rules/mod.rs freshness test trips DEAD001 in 16 crates"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T22:34:25Z"
updated = "2026-10-29T23:49:07Z"
scope = ["crates/gob-rules/**", "crates/gob-check/tests/product_rules/*/src/rules/mod.rs", "crates/crunk-rules/src/rules/mod.rs", "crates/frob-ack/src/rules/mod.rs", "crates/frob-lease/src/rules/mod.rs", "crates/frob-ledger/src/rules/mod.rs", "crates/frob-obligations/src/rules/mod.rs", "crates/frob-pm/src/rules/mod.rs", "crates/frob-release/src/rules/mod.rs", "crates/frob-tests/src/rules/mod.rs", "crates/gob-config/src/rules/mod.rs", "crates/grimble-arch/src/rules/mod.rs", "crates/grimble-bind/src/rules/mod.rs", "crates/grimble-capabilities/src/rules/mod.rs", "crates/grimble-ci/src/rules/mod.rs", "crates/grimble-lints/src/rules/mod.rs", "crates/grimble-model/src/rules/mod.rs", "docs/design/rule-authoring.md", "crates/grimble-check/src/rules/mod.rs"]

[[acceptance]]
text = "The rules-index generator emits a cfg(test) mod tests so DEAD001 no longer flags the freshness test"
bound = false
+++

The rules-index generator (crates/gob-rules/src/indexgen.rs:290) emits 'mod freshness' holding fn rules_index_is_fresh. grimble_bind::eval::is_test_unit only treats a qualifier segment named tests or test as test code, so DEAD001 reports the #[test] fn as dead in every crate with a generated src/rules/mod.rs. Found while burning down ~XVC7KX6. Fix: root #[test] fns in is_test_unit (crates/grimble-bind), or emit 'mod tests' and regenerate every crate index.
