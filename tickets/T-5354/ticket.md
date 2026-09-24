---
id: T-5354
title: 'WEBSEC226-230: randomness and TLS verification'
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
- tests/fixtures/webapp/websec2xx/random_tls/**
- src/frob/webapp/_websec_random_tls.py
- tests/unit/test_websec_random_tls.py
- docs/modules/webapp-websec-random-tls.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec2xx/**
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/webapp/_websec_crypto_tls.py
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec2xx/random_tls/**
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/webapp/_websec_random_tls.py
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_random_tls.py
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-random-tls.md
  reason: per-ticket fixture subdir to avoid session/auth sibling lease collision;
    module renamed to _websec_random_tls.py per coordinator naming; scope test file
    + doc per playbook convention
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
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
Math.random()/random.random() used for a token/session-id/API-key/CSRF-token (name-based heuristic on the assignment target, PERF-family lexical-smell precedent), TLS verification disabled (requests verify=False/rejectUnauthorized:false/literal http:// to an API), TLS minimum version config, certificate pinning (mobile-only, config advisory), credential-stuffing rate-limit cross-refs 5144-2's rate-limit rule. HSTS is owned by T-5143-2's header-lint substrate, NOT this leaf -- this leaf blocks on it rather than reimplementing header parsing. Fixture per rule id.