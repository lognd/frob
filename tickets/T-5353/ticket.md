---
id: T-5353
title: 'WEBSEC218-225: password policy and storage'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5349
parent: T-5142
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
worktree: null
branch: null
scope:
- src/frob/webapp/_websec_password.py
- tests/fixtures/webapp/websec2xx/password/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec2xx/**
  reason: per-ticket fixture subdir, siblings own csrf_session/** (T-5351) and jwt_oauth/**
    (T-5352)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec2xx/password/**
  reason: per-ticket fixture subdir, siblings own csrf_session/** (T-5351) and jwt_oauth/**
    (T-5352)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
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
---
Email verification gating privileged actions, breach-password check (NIST 800-63B 5.1.1.2), password hashing algorithm (bcrypt/argon2/scrypt vs md5/sha1/plaintext), ECB mode, static IV/nonce reuse, default accounts in seed/migration data, password verified without silent truncation/case-folding. AST lint per sink. Fixture per rule id.