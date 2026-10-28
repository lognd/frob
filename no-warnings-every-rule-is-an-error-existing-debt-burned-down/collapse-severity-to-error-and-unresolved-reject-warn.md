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
updated = "2026-10-28T17:21:35Z"
labels = ["no-story"]
scope = ["crates/gob-rules/src/**", "crates/crunk-rules/**", "crates/frob-ack/**", "crates/frob-check/**", "crates/frob-obligations/**", "crates/frob-pm/**", "crates/gob-check/**", "crates/gob-directives/**", "crates/gob-macros/**", "crates/gob-mdtest/**", "crates/grimble-arch/**", "crates/grimble-check/**", "crates/grimble-ci/**", "crates/grimble-lints/**", "crates/grimble-model/**", "crates/gob-diagnostics/**", "crates/crunk-check/**", "crates/crunk-spec/**", "crates/frob-release/**", "crates/frob/**", "crates/grimble-vet/**", "crates/gob-plan/**", "crates/gob-product/**", "crates/grimble-bind/src/rules/**", "crates/grimble-bind/src/eval.rs", "crates/grimble-capabilities/src/pack_rules/**", "packs/**", "docs/design/rule-authoring.md", "docs/design/rules.md", "docs/design/cli.md", "docs/design/architecture.md", "grimble.toml", "frob.toml", "crates/gob-dev/**", "crates/gob-ir/**", "crates/gob-packs/**", "crates/grimble/**", "docs/crunk/**", "docs/schemas/**", "docs/design/policy-snapshot.md", "docs/reference/**", "docs/design/grl-spec.md", "crates/grimble-bind/src/drift.rs", "crates/grimble-capabilities/tests/pack_rules.rs"]

[[acceptance]]
text = "Severity has only Error and Unresolved; Warn and Advisory removed from derive, [rules], fail_on"
bound = false

[[acceptance]]
text = "A config naming warn or advisory is a config error naming error-plus-baseline or off"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.1). Filed from ~ZHW5Y2M.

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
