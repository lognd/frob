---
id: T-5331
title: 'WEBSEC318-325: CI/supply-chain hardening'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5143
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_supply_chain.py
- tests/fixtures/webapp/websec3xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Secrets in CI logs (workflow YAML lint for un-masked env echo), GitHub Actions pinned by tag not SHA, pull_request_target misuse (checkout of fork head + secrets use), Dockerfile running as root (no USER before entrypoint), Dockerfile :latest tag, lockfile presence/sync, typosquat edit-distance on newly added dependencies (bundled top-1000-per-ecosystem list, best-effort not exhaustive). YAML parse (reuse frob's existing GH-Actions YAML parsing if one exists, grep before adding a dependency) + Dockerfile line-scan + manifest/lockfile presence check. Fixture per rule id.