+++
id = "01M64WSNR41TCVNG5F8HH6N6BT"
title = "Generated rules/mod.rs freshness test trips DEAD001 in 16 crates"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T22:34:25Z"
updated = "2026-10-29T22:34:25Z"
scope = ["crates/gob-rules/**"]
+++

The rules-index generator (crates/gob-rules/src/indexgen.rs:290) emits 'mod freshness' holding fn rules_index_is_fresh. grimble_bind::eval::is_test_unit only treats a qualifier segment named tests or test as test code, so DEAD001 reports the #[test] fn as dead in every crate with a generated src/rules/mod.rs. Found while burning down ~XVC7KX6. Fix: root #[test] fns in is_test_unit (crates/grimble-bind), or emit 'mod tests' and regenerate every crate index.
