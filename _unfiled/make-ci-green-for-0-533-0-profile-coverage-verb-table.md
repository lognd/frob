+++
id = "01M6VRR46TR8D8C4TG0GYNK2NK"
title = "Make CI green for 0.533.0: profile coverage, verb table, explain table, layering, family owners, lock, coh004, web conformance"
type = "bug"
category = "in-progress"
priority = "critical"
class = "expedite"
reporter = "lognd"
created = "2026-11-07T19:46:12Z"
updated = "2026-11-07T20:28:31Z"
idempotency_key = "ci-green-533-20261107"
scope = ["crates/gob-dev/**", "crates/frob-docgen/**", "crates/gob-rules/**", "crates/gob-packs/**", "crates/grimble-check/**", "crates/frob/**", "packs/core-effects/**", "grimble.packs.lock", "crates/frob-obligations/**", "docs/design/shared/cli-contract.md", "docs/reference/rules/COH004.md", "crates/grimble-bind/tests/binding_cells.rs", "crates/grimble-lints/src/testq.rs", "crates/grimble-lints/src/testq/model.rs", "crates/grimble-lints/src/unity.rs", "crates/grimble-lints/src/unity_model.rs", "crates/grimble-lints/src/unity_physics.rs", "crates/grimble-lints/src/unity_hot.rs"]

[[acceptance]]
text = "The ubuntu nextest failures in gob-dev, gob-rules, gob-packs and frob-cli (profile coverage, layering, family owners, core-effects lock, explain table, TypeScript COV001) pass"
bound = true
+++
