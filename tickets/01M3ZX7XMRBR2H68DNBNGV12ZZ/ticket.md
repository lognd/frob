+++
id = "01M3ZX7XMRBR2H68DNBNGV12ZZ"
title = "config diff --base REF"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:36Z"
updated = "2026-10-19T07:17:01Z"
idempotency_key = "m2-sec-config-diff"
labels = ["milestone:2", "area:security"]
scope = ["crates/frob/src/config_cmd.rs", "crates/grimble/src/config_diff.rs", "crates/grimble/src/config_for.rs", "crates/grimble/src/lib.rs", "crates/grimble/src/init.rs", "crates/grimble/Cargo.toml", "crates/grimble/tests/verbs.rs", "docs/design/security.md", "docs/design/cli.md", "changelog.d/01M3ZX7XMRBR2H68DNBNGV12ZZ.added.md", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7XBY8S4DXNFVYWVF8884"

[[acceptance]]
text = "Given base and head refs with a weakened policy, when `config diff --base REF` runs with --json, then the weakening entries are listed"
bound = false

[[acceptance]]
text = "Given `init` in a repository without CODEOWNERS covering the control plane, when it runs, then a CODEOWNERS recommendation is printed"
bound = false
+++

Implements security.md section 2.7.

Prints the delta GATE001 would read; init recommends CODEOWNERS for the control plane.
