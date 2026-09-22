---
id: T-draft-7fb71591
title: 'WEBSEC117-122: header/URL/log injection and WebSocket origin check'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5141
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_headers_log.py
- tests/fixtures/webapp/websec1xx/**
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
URL-building injection (missing urlencode/scheme allowlist), CRLF/header injection (response.setHeader from unvalidated input), log injection (f-string/concat of request data into a logger with no CR/LF-stripping encoder), HTML injection in transactional email, Content-Disposition/filename encoding (RFC 6266), field over-exposure (jsonify(model.__dict__) style whole-object serialization), backend following redirects from untrusted URLs (SSRF-adjacent), and WebSocket origin-check + WSS-only enforcement (ASVS V4.4.1/V4.4.2) -- this leaf is the canonical owner of the WebSocket-origin rule; T-5143-5 (config/headers story) cross-references this leaf's rule id rather than reimplementing it. Fixture per rule id.