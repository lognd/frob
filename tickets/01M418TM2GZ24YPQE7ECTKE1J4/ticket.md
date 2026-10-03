+++
id = "01M418TM2GZ24YPQE7ECTKE1J4"
title = "Lockfiles serialize every parallel ticket: [lease] shared_files defaults to empty and nothing points to it"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T16:16:18Z"
updated = "2026-10-03T16:47:48Z"
scope = ["crates/frob-lease/src/config.rs", "crates/frob-lease/src/store.rs", "crates/frob-lease/tests/**", "crates/frob-land/**", "docs/design/tickets.md", "crates/frob-lease/src/verbs.rs", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given no [lease] shared_files and two tickets whose scopes overlap only on Cargo.lock, when the second runs frob work, then it leases without E-LEASE-HELD"
bound = true

[[acceptance]]
text = "Given [lease] shared_files = [] set explicitly and the same overlap, when frob work runs, then E-LEASE-HELD names [lease] shared_files in the remedy"
bound = true

[[acceptance]]
text = "Given two landed tickets that each changed Cargo.lock, when the second lands, then land regenerates the lockfile instead of failing on the conflict"
bound = true
+++

Reported by goway (2026-10-03): two tickets both listing Cargo.lock in scope fail with E-LEASE-HELD overlap: Cargo.lock, so every dependency-adding Rust ticket runs one at a time. [lease] shared_files exists and is honoured by overlap and SCOPE001, but defaults to empty, init does not set it, and the remedy does not name it. Fix: (1) when [lease] shared_files is unset, default to the well-known generated lockfiles (Cargo.lock, uv.lock, poetry.lock, package-lock.json, pnpm-lock.yaml, yarn.lock, go.sum, Gemfile.lock, composer.lock, flake.lock); an explicit value replaces the default. (2) An E-LEASE-HELD whose overlap is only files matching a lockfile pattern names [lease] shared_files in the remedy. (3) At land, a textual merge conflict confined to a shared lockfile is resolved by taking the base side and regenerating it with the ecosystem's offline resolver where one is configured (Cargo: cargo metadata --offline or cargo update --workspace --offline), otherwise refused with a clear remedy.
