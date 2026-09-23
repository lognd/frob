---
id: T-5308
title: 'WEBSEC117-122: header/URL/log injection and WebSocket origin check'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5307
parent: T-5141
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
- src/frob/webapp/_websec_headers_log.py
- tests/fixtures/webapp/websec1xx/headers_log/**
- docs/modules/webapp-websec-headers-log.md
- tests/unit/test_websec_headers_log.py
- src/frob/gates/_taint_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec1xx/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/websec1xx/headers_log/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-websec-headers-log.md
  reason: own doc file for the T-5308 leaf
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_websec_headers_log.py
  reason: unit test binding frob:tests
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: wire WEBSEC117-122 plus sibling discovery
  actor: logan
  at: '2026-09-23'
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
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_websec_headers_log.py::test_websec_headers_log_findings_fixture
- tests/unit/test_websec_headers_log.py::test_websec_headers_log_findings_no_framework_short_circuits
- tests/unit/test_websec_headers_log.py::test_websec_findings_hook_emits_gate_violation
- tests/unit/test_websec_headers_log.py::test_websec_findings_hook_empty_frameworks_short_circuits
- tests/unit/test_websec_headers_log.py::TestTaintGateDiscovery::test_taint_gate_emits_websec117_violation
- tests/unit/test_websec_headers_log.py::TestTaintGateDiscovery::test_discovery_finds_a_planted_fake_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5308
branch: t-5308
---
URL-building injection (missing urlencode/scheme allowlist), CRLF/header injection (response.setHeader from unvalidated input), log injection (f-string/concat of request data into a logger with no CR/LF-stripping encoder), HTML injection in transactional email, Content-Disposition/filename encoding (RFC 6266), field over-exposure (jsonify(model.__dict__) style whole-object serialization), backend following redirects from untrusted URLs (SSRF-adjacent), and WebSocket origin-check + WSS-only enforcement (ASVS V4.4.1/V4.4.2) -- this leaf is the canonical owner of the WebSocket-origin rule; T-5143-5 (config/headers story) cross-references this leaf's rule id rather than reimplementing it. Fixture per rule id.