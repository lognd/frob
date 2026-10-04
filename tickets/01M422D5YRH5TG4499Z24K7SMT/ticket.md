+++
id = "01M422D5YRH5TG4499Z24K7SMT"
title = "Dev build fails: dist now archives frob-check's test helper binary; ship exactly one archive per product binary"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T23:43:20Z"
updated = "2026-10-04T01:58:13Z"
scope = ["crates/frob-check/Cargo.toml", "crates/frob-check/tests/**", "dist-workspace.toml", "packaging/smoke/**", ".github/workflows/build-smoke.yml", ".github/workflows/ci.yml", ".github/workflows/release.yml", "crates/frob-release/tests/**", "docs/design/releases.md", "Cargo.lock", "Cargo.toml", "crates/frob/Cargo.toml", "crates/grimble/Cargo.toml", "crates/gob-testsupport/**", "crates/frob/tests/sibling_discovery.rs"]

[[acceptance]]
text = "Given cargo metadata, when the product-binary test runs, then every publishable package's bin targets are exactly the product binaries"
bound = true

[[acceptance]]
text = "Given dist build for a target, when it finishes, then target/distrib holds exactly one archive per product binary with the product name"
bound = true

[[acceptance]]
text = "Given the build-smoke workflow, when its tests run, then the smoke step names each product archive and runs each binary"
bound = true
+++

First dev-channel run (CI 37161273161, 2026-10-03): tests green on both platforms, then the dev build failed on 4 of 5 targets in the archive smoke: target/distrib held three archives (frob-check-<t>, frob-cli-<t>, grimble-<t>) and the smoke step expects one (ls *.tar.xz). Since ~AZS0RRT made crates publishable, dist distributes every publishable package with a binary: frob-check ships the test helper binary fake-sibling (crates/frob-check/Cargo.toml [[bin]] tests/support/fake_sibling.rs), which would also be published to crates.io and installed by cargo install frob-check.

Fix structurally:
1. Test helpers never ship: move fake-sibling out of the published frob-check crate into a publish = false test-support crate (or gob-dev / gob-mdtest), or build it from the test with a test-only mechanism; no published crate may declare a [[bin]] that is not a product. Add a test over cargo metadata: every publishable package's bin targets are exactly the product binaries (frob from frob-cli, grimble from grimble).
2. dist distributes exactly the product list (D87, products.md 6): one archive per product binary per target (frob, grimble; crunk later as one entry), everything else dist = false by default (workspace-level default plus per-product opt-in), with a test that the dist package set equals the product list. Decide and document the archive names (frob-<target> vs frob-cli-<target>) so users and the dev and release assets see the product name.
3. The archive smoke (packaging/smoke/archive-smoke.sh and the build-smoke.yml step) iterates over the product archives explicitly by name, smoking each binary, instead of globbing one file; the dev publish and the release job upload every product archive and checksum; update dev_workflow and release_workflow tests (asset names, counts).
This blocks the dev channel and the release.
