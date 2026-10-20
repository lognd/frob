+++
id = "01M47QV3BRRZZSMJ5Q79N8G5S2"
title = "cargo-fuzz targets for every parser and the ledger fold, built on every PR"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:08Z"
updated = "2026-10-06T04:34:08Z"
scope = ["fuzz/**", "crates/gob-dev/**", ".github/workflows/**", "Cargo.toml"]

[[acceptance]]
text = "fuzz targets exist for the five inputs"
bound = false

[[acceptance]]
text = "the fuzz-build step builds and runs them briefly"
bound = false

[[acceptance]]
text = "the nightly job is documented and pinned by SHA"
bound = false
+++

build-test-ci.md section 6, ruff fuzz/. A fuzz/ crate (excluded from the workspace members' publish) with targets for GRL, .grmb, directives, crunk.toml and ledger event decoding plus fold: no panic, and round-trip where a printer exists. A fuzz-build cargo dev ci step builds them on PRs and runs each 60 s; a nightly workflow runs longer and files a ticket per crash.
