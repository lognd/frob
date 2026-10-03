+++
id = "01M41ZJGQ1GKF6NJ1JV25QHMNX"
title = "Dev channel never runs: workflow_run fires only from the default branch; make it a gated job in ci.yml"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T22:53:49Z"
updated = "2026-10-03T23:16:32Z"
scope = [".github/workflows/ci.yml", ".github/workflows/dev.yml", "crates/frob-release/tests/**", "crates/gob-dev/tests/ci_parity.rs", "docs/design/releases.md", "docs/guides/release.md", ".github/workflows/build-smoke.yml", ".github/workflows/release.yml", "frob.lock"]

[[acceptance]]
text = "Given a push to experimental whose test jobs pass, when ci.yml runs, then the dev publish job runs in the same workflow and no workflow_run trigger exists anywhere"
bound = true

[[acceptance]]
text = "Given a pull request or a push to another branch, when ci.yml runs, then the dev publish job is skipped"
bound = true

[[acceptance]]
text = "Given the moved invariant tests, when they run, then every dev_workflow invariant holds against the job in ci.yml"
bound = true
+++

First green CI on experimental (run 37158875783, 2026-10-03) published no dev prerelease: dev.yml triggers on workflow_run of ci, and GitHub only runs workflow_run workflows whose file is on the default branch (main, which still holds v1's workflows). workflow_run is also the dangerous trigger zizmor flags (CI006, accepted in dev.yml). Replace it: the dev publish becomes the last job of ci.yml, needs every test job, runs only on push to the configured dev branches (experimental) of this repository (if on github.ref and github.repository, no pull_request), holds the only contents: write, and calls the shared build-smoke workflow as dev.yml does today; delete dev.yml and its CI006 accept. Keep every invariant the dev_workflow tests pin (add-then-prune, cleanup of this run's uploads only, never publishes to registries, SHA pins, timeouts) by moving those tests to read the job in ci.yml. The parity test (~AHBKXAZ) must still pass: publishing is not a cargo dev ci step.
