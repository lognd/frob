+++
id = "01M3ZX7HCQYMTNB9S8ANCZA04W"
title = "rule new: scaffold a rule from FILE:LINE"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:23Z"
updated = "2026-10-12T00:27:19Z"
idempotency_key = "m2-grl-new"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/verbs/new.rs", "crates/gob-plan/src/verbs/mod.rs", "crates/grimble/src/rule_cmd.rs", "crates/grimble/src/lib.rs", "crates/frob/src/rule_cmd.rs", "crates/frob/src/product.rs", "crates/gob-dev/profile.toml", "crates/grimble/tests/rule_verbs.rs", "crates/gob-plan/tests/verbs.rs", "crates/gob-plan/tests/rule_new.rs", "docs/reference/cli/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DG5711ZSC4R0Y64C78A"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E5VPTH8J16D5APQDEAP"

[[acceptance]]
text = "Given src/parse.rs:42 containing `dbg!(tokens.len())`, when `rule new NOPE001 --from src/parse.rs:42` runs, then rules/NOPE001.grl contains `find d: `dbg!($$$ARGS)``, a fire example from that line and an explain stub"
bound = true

[[acceptance]]
text = "Given the scaffold, when `rule check` runs on it, then the only error is GRL011 for the missing clean example"
bound = true
+++

Implements grl-spec.md sections 2 and 11.

Turn the code at a location into a snippet with names turned into metavariables, a fire example from that code, an empty clean example and an explain stub.
