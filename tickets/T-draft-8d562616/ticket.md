---
id: T-draft-8d562616
title: 'M1: frob v2 self-hosts (checks and lands this repository)'
state: queued
kind: feature
origin: human
created: '2026-10-02'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 13
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- crates/**
- Cargo.toml
- .cargo/**
- .github/**
scope_breadth_ack: true
scope_breadth_ack_reason: milestone epic; children carry the real per-crate scopes
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given this repository with the v2 workspace, when a developer runs frob check
    from a fresh process with a warm cache, then it finishes green in under 2 seconds
    and reports findings for DRIFT COV TODO DOC REF INV TICK SCOPE TEST
  evidence: []
- text: Given a ticket worked in a frob worktree, when the agent runs frob land, then
    the ticket closes synchronously with bound evidence and the ledger commit lands
    on the configured ledger ref
  evidence: []
- text: Given the design docs, when any M1 child deviates from docs/design, then the
    deviation is recorded as a decision-log proposal in the done-report
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Milestone 1 per decision D36 and the cut table at the end of notes/audit-design.md: frob checks and lands in this repository with Rust, markdown and TOML adapters only. No grimble, crunk, GUI, daemon, jobs, salsa, IR, PM forecasting or Jira-parity features. Children are one ticket per crate group in dependency order; see notes/coordinator.md.