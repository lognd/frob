+++
id = "01M4CTE2T943ATA1PKVBN7DCP3"
title = "CI hygiene: concurrency cancel, paths filters, job timeouts, drop checks run twice, fold the Windows isolated-tool duplicates (audit M18)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:40Z"
updated = "2026-10-10T02:22:46Z"
scope = ["changelog.d/**", ".github/workflows/ci.yml", ".github/workflows/build-smoke.yml", "crates/gob-dev/src/ci.rs", "crates/gob-dev/tests/ci_parity.rs", "docs/design/releases.md"]

[[acceptance]]
text = "Given a second push to the same ref, when CI starts, then the earlier run is cancelled"
bound = true

[[acceptance]]
text = "Given every CI job, when inspected, then each has timeout-minutes and no check runs twice per OS"
bound = true

[[acceptance]]
text = "Given several pushes to experimental within minutes, when CI runs, then a concurrency group per workflow and ref cancels the superseded in-progress run (never for release or publish jobs), so only the newest commit's run completes"
bound = true

[[acceptance]]
text = "Given a push that changes only tickets/**, changelog.d/** or docs/** (docs not under generated reference checks), when CI triggers, then the Rust jobs are skipped by paths filters and a cheap docs job runs instead"
bound = true

[[acceptance]]
text = "Given the dev-artifacts job, when experimental is green, then it builds at most once per hour or only for the newest green commit, not on every land; and workspace crates are cached across runs (sccache with the GitHub Actions cache backend, or rust-cache cache-workspace-crates) with the measured hit rate reported"
bound = true
+++

notes/review/audit-2026-10-07.md M18. Keep zizmor and actionlint clean. Coordinate with ~RWD03DW, which adds the profile job to ci.yml: land after it or rebase onto it.
