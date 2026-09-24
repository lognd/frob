---
id: T-5306
title: 'WEBSEC101-108: output-encoding and template sinks'
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
- src/frob/webapp/_websec_xss.py
- tests/fixtures/webapp/websec1xx/xss/**
- docs/modules/webapp-websec-xss.md
- tests/unit/test_websec_xss.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec1xx/**
  reason: narrow to xss subdir, sibling leaves (T-5308 headers) share websec1xx root
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/websec1xx/xss/**
  reason: narrowed fixture subdir so sibling websec1xx leaves (T-5308 etc) can run
    concurrently
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-websec-xss.md
  reason: doc citation + unit test binding for new symbols
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_websec_xss.py
  reason: doc citation + unit test binding for new symbols
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
evidence:
- tests/unit/test_websec_xss.py::test_taint_gate_discovers_websec_xss_hook
- tests/unit/test_websec_xss.py::test_websec_xss_findings_fixture[webesc107_positive-WEBSEC107-True]
- tests/unit/test_websec_xss.py::test_websec_xss_findings_fixture[webesc107_negative-WEBSEC107-False]
- tests/unit/test_websec_xss.py::test_websec_xss_findings_fixture[webesc108_positive-WEBSEC108-True]
- tests/unit/test_websec_xss.py::test_websec_xss_findings_fixture[webesc108_negative-WEBSEC108-False]
- tests/unit/test_websec_xss.py::test_websec_xss_findings_no_framework_short_circuits
- tests/unit/test_websec_xss.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_websec_xss.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5306
branch: t-5306
---
Rule ids WEBSEC101 (reflected/stored XSS encoding, ASVS V1.2.1), 102 (innerHTML/outerHTML/document.write/insertAdjacentHTML JS/TS AST), 103 (dangerouslySetInnerHTML JSX), 104 (v-html Vue SFC), 105 (Jinja |safe/autoescape=False regex), 106 (Django mark_safe/autoescape-off Python AST + template regex), 107 (Rails .html_safe/raw() regex), 108 (PHP echo of superglobals without htmlspecialchars, regex). Dispatched by framework detection (WEBSUB-2) so a Django-only repo never runs the Rails rule. Fixture: one planted finding per rule id.