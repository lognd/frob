+++
id = "01M3WYJ802ZVWE6E3050EVRCSV"
title = "M1: frob v2 self-hosts (checks and lands this repository)"
type = "epic"
category = "done"
outcome = "done"
priority = "high"
points = 13
reporter = "human"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-06T07:54:42Z"
aliases = ["T-0002"]
labels = ["milestone:2.0.0"]
scope = ["crates/**", "Cargo.toml", ".cargo/**", ".github/**"]

[[acceptance]]
text = "Given this repository with the v2 workspace, when a developer runs frob check from a fresh process with a warm cache, then it finishes green in under 2 seconds and reports findings for DRIFT COV TODO DOC REF INV TICK SCOPE TEST"
bound = false

[[acceptance]]
text = "Given a ticket worked in a frob worktree, when the agent runs frob land, then the ticket closes synchronously with bound evidence and the ledger commit lands on the configured ledger ref"
bound = false

[[acceptance]]
text = "Given the design docs, when any M1 child deviates from docs/design, then the deviation is recorded as a decision-log proposal in the done-report"
bound = false
+++

Milestone 1 per decision D36 and the cut table at the end of notes/audit-design.md: frob checks and lands in this repository with Rust, markdown and TOML adapters only. No grimble, crunk, GUI, daemon, jobs, salsa, IR, PM forecasting or Jira-parity features. Children are one ticket per crate group in dependency order; see notes/coordinator.md.
