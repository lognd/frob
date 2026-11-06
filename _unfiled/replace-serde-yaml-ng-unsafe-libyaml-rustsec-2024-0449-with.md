+++
id = "01M4RP0GFBQAGQXK1MGGFBGN4Y"
title = "Replace serde_yaml_ng (unsafe-libyaml, RUSTSEC-2024-0449) with a maintained YAML parser and drop the deny.toml ignore"
type = "chore"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-12T18:29:14Z"
updated = "2026-11-06T08:21:40Z"
scope = ["crates/grimble-ci/**", "crates/frob-release/**", "crates/frob-evidence/**", "deny.toml", "Cargo.lock", "Cargo.toml", "docs/**", "crates/gob-dev/**", ".grimble/vet.toml"]
+++

gob-dev and frob-release (dev) use serde_yaml_ng, which pulls the archived unsafe-libyaml. Swap to serde-saphyr or similar, then remove the ignore in deny.toml. Acceptance: cargo deny check advisories passes with ignore = [].
