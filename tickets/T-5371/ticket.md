---
id: T-5371
title: 'WEBPERF101-108: Core Web Vitals causes in markup'
state: done
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
parent: T-5147
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5371
branch: t-5371
scope:
- src/frob/webapp/_webperf_markup.py
- tests/fixtures/webapp/webperf1xx/markup/**
- tests/unit/test_webapp_webperf_markup.py
- docs/modules/webapp-webperf-markup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/webperf1xx/**
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/webperf1xx/markup/**
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webapp_webperf_markup.py
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-webperf-markup.md
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf101_positive-WEBPERF101-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf101_negative-WEBPERF101-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf102_positive-WEBPERF102-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf102_negative-WEBPERF102-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf103_positive-WEBPERF103-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf103_negative-WEBPERF103-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf104_positive-WEBPERF104-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf104_negative-WEBPERF104-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf105_positive-WEBPERF105-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf105_negative-WEBPERF105-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf106_positive-WEBPERF106-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf106_negative-WEBPERF106-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf108_positive-WEBPERF108-True]
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf108_negative-WEBPERF108-False]
- tests/unit/test_webapp_webperf_markup.py::test_webperf107_never_emitted
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_no_framework_short_circuits_via_hook
- tests/unit/test_webapp_webperf_markup.py::test_websec_findings_discovery_hook_emits_violation
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Image width/height for CLS, loading=lazy on offscreen img/iframe, srcset, font-display, defer/async on head scripts, bundle-budget config assertion (webpack/vite), source-maps-in-prod cross-refs T-5143-3, not duplicated. Tree-sitter query over HTML/JSX (5147-1 substrate). Fixture per rule id.