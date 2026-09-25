---
id: T-6486
title: 'SYSDESIGN402: session middleware configured with an in-memory/file-based backend'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6410
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
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
- src/frob/sysdesign/_horizontal.py
- tests/fixtures/sysdesign/sysdesign402/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN402: session middleware configured with an in-memory/file-based backend
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN402 row),
       tests/fixtures/sysdesign/sysdesign402/**
blocked_by: []
tag: Static: config

Research row 7.2: The Twelve-Factor App, "VI. Processes", https://12factor.net/processes --
"Session state data is a good candidate for a datastore that offers time-expiration, such as
Memcached or Redis." Lint condition: "Web framework session middleware configured with an
in-memory/file-based session backend in a production deployment target flags."

Acceptance criteria: detects framework session-middleware configuration (Django `SESSION_
ENGINE`, Express `express-session` store option, Flask `SESSION_TYPE`, etc.) set to an
in-memory or filesystem backend for a target the design model declares "production". Positive-
control fixture: tests/fixtures/sysdesign/sysdesign402/filesystem-session-backend/**.
