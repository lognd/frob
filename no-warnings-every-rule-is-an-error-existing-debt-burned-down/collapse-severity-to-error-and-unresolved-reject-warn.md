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
updated = "2026-10-28T12:54:56Z"
scope = ["crates/gob-rules/src/**", "crates/crunk-rules/Cargo.toml", "crates/crunk-rules/src", "crates/crunk-rules/tests", "crates/frob-ack/Cargo.toml", "crates/frob-ack/src", "crates/frob-ack/tests", "crates/frob-check/Cargo.toml", "crates/frob-check/benches", "crates/frob-check/clippy.toml", "crates/frob-check/src", "crates/frob-check/tests", "crates/frob-obligations/Cargo.toml"]

[[acceptance]]
text = "Severity has only Error and Unresolved; Warn and Advisory removed from derive, [rules], fail_on"
bound = false

[[acceptance]]
text = "A config naming warn or advisory is a config error naming error-plus-baseline or off"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.1). Filed from ~ZHW5Y2M.
