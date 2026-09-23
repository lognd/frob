---
id: T-5329
title: 'WEBSEC310-317: debug/info-leak config'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5143
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_debug_config.py
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
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DEBUG=True in prod, source maps deployed to prod (webpack/vite config AST for devtool:'source-map' plus build-output .map-file check), verbose stack traces in error handler, directory listing (nginx/Apache config), .git/.svn deployed (deploy-pipeline/Dockerfile COPY lint), public S3/GCS/Supabase buckets (IaC regex-scan for public-read/AllUsers, not a full HCL parser), secrets in front-end bundles (reuses 5141-1's secret-pattern table, grepped against compiled JS output -- does not reimplement it). Default-creds cross-refs SEC001-003, not duplicated here. Fixture per rule id.