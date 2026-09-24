---
id: T-5331
title: 'WEBSEC318-325: CI/supply-chain hardening'
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5302
parent: T-5143
tier: ticket
sprint: null
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
- tests/fixtures/webapp/websec3xx/supply/**
- tests/unit/test_websec_supply_chain.py
- docs/modules/webapp-websec-supply-chain.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec3xx/**
  reason: per-ticket fixture subdir so the four headers leaves do not lease-collide
    on the shared glob
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec3xx/supply/**
  reason: per-ticket fixture subdir so the four headers leaves do not lease-collide
    on the shared glob
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_supply_chain.py
  reason: unit test + doc for the new module, per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-supply-chain.md
  reason: unit test + doc for the new module, per playbook convention
  actor: logan
  at: '2026-09-24'
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
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5331
branch: t-5331
---
Secrets in CI logs (workflow YAML lint for un-masked env echo), GitHub Actions pinned by tag not SHA, pull_request_target misuse (checkout of fork head + secrets use), Dockerfile running as root (no USER before entrypoint), Dockerfile :latest tag, lockfile presence/sync, typosquat edit-distance on newly added dependencies (bundled top-1000-per-ecosystem list, best-effort not exhaustive). YAML parse (reuse frob's existing GH-Actions YAML parsing if one exists, grep before adding a dependency) + Dockerfile line-scan + manifest/lockfile presence check. Fixture per rule id.