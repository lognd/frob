+++
id = "01M67V5EMARFQB1H20A39CBAEM"
title = "CI: fix rustdoc private-link errors and profile.toml missing scenarios"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-31T02:03:37Z"
updated = "2026-10-31T02:26:20Z"
idempotency_key = "ci-green-1031"
scope = ["crates/grimble-model/src/args.rs", "crates/gob-dev/profile.toml"]

[[acceptance]]
text = "cargo doc private intra-doc links to MAX_LINK_HOPS are fixed so the docs CI step passes on Linux and Windows"
bound = true

[[acceptance]]
text = "profile.toml has a scenario or skip reason for frob baseline adopt, frob baseline prune and frob migrate so the profile CI job passes"
bound = true
+++

CI run 41157214562 failed: docs (rustdoc private link MAX_LINK_HOPS in grimble-model args.rs) and profile (leaf commands without scenario).
