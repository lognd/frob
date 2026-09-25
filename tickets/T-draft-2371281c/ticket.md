---
id: T-draft-2371281c
title: 'SYSDESIGN401: request-scoped data written to local disk/in-process cache reused
  across requests'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-3ed25d21
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
- src/frob/sysdesign/_horizontal.py (new)
- tests/fixtures/sysdesign/sysdesign401/**
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
title: SYSDESIGN401: request-scoped data written to local disk/in-process cache reused across
       requests (statelessness smell)
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py (new), docs/modules/gates.md (SYSDESIGN401 row),
       tests/fixtures/sysdesign/sysdesign401/**
blocked_by: []
tag: Static: code

Research row 7.1: The Twelve-Factor App, "VI. Processes", https://12factor.net/processes --
"Twelve-factor processes are stateless and share-nothing... The twelve-factor app never assumes
that anything cached in memory or on disk will be available on a future request or job." Also
AWS Well-Architected Reliability Pillar REL05-BP06: "Systems should either not require state, or
should offload state such that between different client requests, there is no dependence on
locally stored data on disk and in memory." Lint condition: "Code path writing request-scoped
'durable' data to local disk or an in-process cache keyed for reuse across requests (not a
single-request-scoped cache) flags."

Acceptance criteria: detects a write to local filesystem or a module-level/process-lifetime
dict/cache keyed by a request-derived identifier (session id, user id) outside an explicitly
declared single-request scope. Positive-control fixture: tests/fixtures/sysdesign/sysdesign401/
local-disk-session-write/**.
