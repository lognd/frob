+++
id = "01M4YDMAEVVMXZG161VGAT7S84"
title = "Tests: inject env and PATH into Context so more frob CLI tests run in process; consolidate remaining crates; re-measure suite wall time (follow-up to ~E0E8M28)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-14T23:58:12Z"
updated = "2026-10-28T12:55:54Z"
labels = ["no-story"]
scope = ["crates/*/tests/**", "crates/gob-cli/src/**"]

[[acceptance]]
text = "Given the ci nextest profile, when the full suite runs on quasar, then wall time is at least 25 percent below a same-host baseline taken at the parent commit, with no test removed"
bound = false
+++

Left by ~E0E8M28: remaining per-crate consolidation (frob-ledger, crunk-*, grimble-*, frob-tests, gob-dev; gob-plan after ~0HC06TD and ~YJPYE5V land), Context-injected env and PATH so tests that set .env or need hermetic PATH run in process, routing the remaining direct cargo_bin spawns through frob_command(), and a workspace-wide A/B wall-time measurement (not possible under the OOM-era -j2 limits). Do not consolidate trybuild binaries (ui, ui_rule_attr, ui_product).

no-story: internal engineering task in gob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
