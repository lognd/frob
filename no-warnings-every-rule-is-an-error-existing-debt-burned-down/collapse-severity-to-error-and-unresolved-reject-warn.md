+++
id = "01M5XMJGNF1HWQBEGE31G4B9C1"
title = "Collapse Severity to Error and Unresolved; reject warn/advisory config"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:01Z"
updated = "2026-10-28T12:55:10Z"
scope = ["crates/gob-rules/src/**", "crates/crunk-rules/Cargo.toml", "crates/crunk-rules/src", "crates/crunk-rules/tests", "crates/frob-ack/Cargo.toml", "crates/frob-ack/src", "crates/frob-ack/tests", "crates/frob-check/Cargo.toml", "crates/frob-check/benches", "crates/frob-check/clippy.toml", "crates/frob-check/src", "crates/frob-check/tests", "crates/frob-obligations/Cargo.toml", "crates/frob-obligations/src", "crates/frob-obligations/tests", "crates/frob-pm/Cargo.toml", "crates/frob-pm/src", "crates/frob-pm/tests", "crates/gob-check/Cargo.toml", "crates/gob-check/clippy.toml", "crates/gob-check/src", "crates/gob-check/tests", "crates/gob-directives/Cargo.toml", "crates/gob-directives/resources", "crates/gob-directives/src", "crates/gob-directives/tests", "crates/gob-macros/Cargo.toml", "crates/gob-macros/src", "crates/gob-macros/tests", "crates/gob-mdtest/Cargo.toml", "crates/gob-mdtest/FORMAT.md", "crates/gob-mdtest/coverage-allowlist.toml", "crates/gob-mdtest/src", "crates/gob-mdtest/tests", "crates/grimble-arch/Cargo.toml", "crates/grimble-arch/src", "crates/grimble-arch/tests", "crates/grimble-check/Cargo.toml", "crates/grimble-check/clippy.toml", "crates/grimble-check/src", "crates/grimble-check/tests", "crates/grimble-ci/Cargo.toml", "crates/grimble-ci/src", "crates/grimble-ci/tests", "crates/grimble-lints/Cargo.toml", "crates/grimble-lints/src", "crates/grimble-lints/tests", "crates/grimble-model/Cargo.toml", "crates/grimble-model/resources", "crates/grimble-model/src", "crates/grimble-model/tests", "crates/gob-diagnostics/Cargo.toml", "crates/gob-diagnostics/src", "crates/gob-diagnostics/tests", "crates/crunk-check/Cargo.toml", "crates/crunk-check/clippy.toml", "crates/crunk-check/src", "crates/crunk-check/tests", "crates/crunk-spec/Cargo.toml", "crates/crunk-spec/data", "crates/crunk-spec/resources", "crates/crunk-spec/src"]

[[acceptance]]
text = "Severity has only Error and Unresolved; Warn and Advisory removed from derive, [rules], fail_on"
bound = false

[[acceptance]]
text = "A config naming warn or advisory is a config error naming error-plus-baseline or off"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.1). Filed from ~ZHW5Y2M.
