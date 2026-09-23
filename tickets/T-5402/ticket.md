---
id: T-5402
title: Add EXPRESS to FrameworkKind and extend WEBSEC authz substrate to Express handlers
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-5356 names Express in its body but frob.webapp._detect.FrameworkKind (T-5302) has no EXPRESS member, so the authz substrate skips Express handlers; documented in docs/modules/webapp-websec-authz.md. Add EXPRESS detection (package.json dependency 'express', app.get/post route shape) in _detect.py with positive/negative fixtures, then teach _websec_authz_substrate to scan Express route handlers for ORM lookups without a req.user/session reference. Scope: src/frob/webapp/_detect.py, src/frob/webapp/_websec_authz_substrate.py, tests/fixtures/webapp/{express,websec4xx/express}/**, tests/unit/test_webapp_detect.py, tests/unit/test_webapp_websec_authz_substrate.py.