---
id: T-5325
title: 'WEBSEC config/headers substrate: response-header lint engine'
state: queued
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
- src/frob/webapp/_websec_headers.py
- tests/fixtures/webapp/websec3xx/**
- docs/modules/webapp-websec-headers.md
- tests/unit/test_webapp_websec_headers.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/webapp-websec-headers.md
  reason: T-5325 owns its own module doc per WEBSEC fan-out convention, docs/modules/webapp.md
    is shared across 7 concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_websec_headers.py
  reason: unit coverage for the new lint_response_headers engine, positive+negative
    controls per family
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
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
  old_value: '3'
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
- tests/unit/test_webapp_websec_headers.py::test_django_full_all_present
- tests/unit/test_webapp_websec_headers.py::test_django_missing_xfo_reports_missing
- tests/unit/test_webapp_websec_headers.py::test_express_helmet_reports_default_headers_present
- tests/unit/test_webapp_websec_headers.py::test_no_evidence_is_advisory_not_error
- tests/unit/test_webapp_websec_headers.py::test_root_not_a_directory_is_err
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_webapp_websec_headers.py::test_nginx_full_all_present
  new_node: ''
  reason: 'T-5325: parametrized into test_full_evidence_all_present, old node id no
    longer resolves'
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_websec_headers.py::test_nginx_missing_csp_reports_missing
  new_node: ''
  reason: 'T-5325: parametrized, old node id no longer resolves'
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_websec_headers.py::test_caddy_full_all_present
  new_node: ''
  reason: 'T-5325: parametrized, old node id no longer resolves'
  actor: logan
  at: '2026-09-23'
- old_node: tests/unit/test_webapp_websec_headers.py::test_caddy_missing_hsts_reports_missing
  new_node: ''
  reason: 'T-5325: parametrized, old node id no longer resolves'
  actor: logan
  at: '2026-09-23'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
HeaderSourceKind union parser: (a) app-code AST lint for helmet(...)/django-secure/SECURE_* settings/manual response.headers[...]= calls, (b) nginx/Caddy config-file line parser for add_header/directive blocks, (c) documented gap for CDN-layer-only header injection (Cloudflare/Fastly dashboards) as a WARN advisory ('no in-repo evidence; confirm at your edge') rather than a false ERROR. Fixture: nginx conf, Django settings, Express+helmet fixture, one with and one without each header.