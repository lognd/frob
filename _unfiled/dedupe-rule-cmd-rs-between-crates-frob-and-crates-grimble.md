+++
id = "01M6EXZE3ARQ1855G1KSNCFGZ5"
title = "Dedupe rule_cmd.rs between crates/frob and crates/grimble"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T20:07:27Z"
updated = "2026-11-02T23:21:30Z"
scope = ["crates/frob/src/**,crates/grimble/src/**,crates/gob-product/src/**", "crates/frob/src/**", "crates/grimble/src/**", "crates/gob-product/src/**", "crates/gob-product/Cargo.toml", "Cargo.lock", "crates/grimble/tests/rule_verbs.rs", "crates/frob/tests/it/rule_why.rs", "crates/frob/Cargo.toml"]

[[acceptance]]
text = "A single shared rule_cmd implementation serves frob and grimble"
bound = true
+++

Follow-up from ~PQV03PB: the two copies of rule_cmd.rs differ only in the product name in #[command], with_pretty vs with_rendered, and two use lines.
