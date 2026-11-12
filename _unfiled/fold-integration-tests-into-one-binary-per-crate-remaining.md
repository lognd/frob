+++
id = "01M5AH5JNAB2APDDP317HGFM86"
title = "Fold integration tests into one binary per crate: remaining crates under crates/*/tests (~243 files), then verify cargo dev test-size under 3 GB"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-19T16:50:57Z"
updated = "2026-11-12T01:29:36Z"
labels = ["no-story"]
scope = ["crates/*/tests/**", ".github/scripts/plan-jobs.py", ".github/workflows/ci.yml", ".github/workflows/dup-scan.yml", "crates/crunk-gallery/README.md", "crates/gob-dev/src/ci.rs", "crates/gob-dev/src/render/inline.rs", "crates/gob-fs/src/lib.rs", "crates/gob-mdtest/FORMAT.md", "crates/gob-mdtest/src/matrix.rs", "crates/grimble/src/lib.rs", "design/model.grmb", "docs/design/dup.md", "docs/design/grimble/grmb-spec.md", "docs/design/shared/architecture.md", "docs/design/shared/build-test-ci.md", "docs/design/shared/charter.md", "docs/design/shared/cli-contract.md", "docs/design/shared/rules.md", "docs/guides/crunk.md"]
+++

found while working ~ZM1HA1J: finishes the consolidation and closes the 3 GB acceptance measurement.

no-story: internal engineering task in crates/*/tests/**; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
