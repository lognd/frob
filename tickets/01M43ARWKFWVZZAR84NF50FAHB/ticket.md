+++
id = "01M43ARWKFWVZZAR84NF50FAHB"
title = "crunk as a frob sibling: discovery, doctor row, fake-sibling and bundle tests"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:47Z"
updated = "2026-10-04T22:18:20Z"
idempotency_key = "crunk-plan-sib"
labels = ["area:crunk"]
scope = ["crates/frob-check/tests/**", "crates/frob-check/src/sibling/**", "crates/frob/tests/sibling_discovery.rs", "crates/frob/src/doctor.rs", "crates/gob-testsupport/**"]

[[links]]
kind = "blocked-by"
target = "01M43ARVS24254G85TMFYH8FGQ"

[[links]]
kind = "blocked-by"
target = "01M43ARWCVRCE25KDZC8CRC1ZH"

[[acceptance]]
text = "Given crunk beside frob and not on PATH and a crunk.toml, when frob check runs, then crunk's findings appear in the merged report"
bound = true

[[acceptance]]
text = "Given crunk versions beside frob and on PATH that differ, when frob doctor runs, then both are reported and the one beside frob is used"
bound = true

[[acceptance]]
text = "Given a crunk whose --json has another schema_version, when frob check runs, then a required Unresolved finding is reported and the exit is 1"
bound = true
+++

Discovery next to frob's own executable is done (~JS1VMBC) and frob-check already lists (crunk, crunk.toml) as a sibling; this ticket proves it for the real crunk: frob check runs `crunk check --json` when crunk.toml exists, merges findings under crunk's family prefixes, doctor lists the crunk copy beside frob and any second copy with its version, an incompatible schema_version is the required Unresolved. Also the crunk-check dependency of the frob `bundle` feature if grimble's is wired (boundaries 6); otherwise record that as follow-up. docs/design/sibling-contract.md.
