---
id: T-5349
title: 'WEBSEC session/CSRF substrate: normalized SessionConfig reader'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5142
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_session_config.py
- tests/fixtures/webapp/websec2xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Framework-specific config-file parse (Django settings.py AST for MIDDLEWARE/SESSION_COOKIE_*; Flask app-factory AST for SESSION_COOKIE_*/app.config[...]; Express app.use(session(...)) call-argument AST; Rails config/initializers/session_store.rb + protect_from_forgery AST) producing one normalized SessionConfig model (secure/httponly/samesite/csrf_middleware_present/idle_timeout/absolute_timeout) every rule below reads instead of re-parsing. Fixture: one config fixture per framework, compliant and violating variants.