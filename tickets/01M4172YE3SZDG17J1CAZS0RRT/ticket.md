+++
id = "01M4172YE3SZDG17J1CAZS0RRT"
title = "Make the full crate set publishable and support a first-publish token in the crates job"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T15:45:53Z"
updated = "2026-10-03T18:05:35Z"
scope = ["Cargo.toml", "crates/*/Cargo.toml", ".github/workflows/release.yml", "crates/frob-release/tests/release_workflow.rs", "docs/design/releases.md", "crates/gob-dev/src/publish.rs", "docs/guides/release.md"]

[[acceptance]]
text = "Given the workspace, when cargo dev publish --dry-run runs, then it plans every shipped crate in dependency order and excludes exactly the listed dev-only crates"
bound = true

[[acceptance]]
text = "Given the release workflow, when its test runs, then the crates job uses a registry token when the environment provides one and the OIDC action otherwise"
bound = true
+++

Follow-up from ~6N2KET1: the workspace root sets publish = false, inherited everywhere, so cargo dev publish --dry-run plans 0 crates. Per products.md 5 and monorepo.md 4 the full crate set publishes in lockstep (frob as frob-cli, gob-*, frob-*, grimble-*), except crates that are dev-only (gob-dev, test harnesses): list them explicitly. Every intra-workspace path dependency needs a version (release bump already writes it; verify). crates.io trusted publishing cannot be set up before a crate exists, so the crates job must accept CARGO_REGISTRY_TOKEN from the crates-io environment when present and use OIDC otherwise; document the one-time token step for the runbook (~H7BCMWX).
