---
id: T-5370
title: 'COMPLY117-122: sector-specific (HIPAA/GLBA/COPPA/FERPA, flag-gated)'
state: done
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5360
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5370
branch: t-5370
scope:
- src/frob/webapp/_comply_sector.py
- tests/fixtures/webapp/comply1xx/sector/**
- tests/unit/test_webapp_comply_sector.py
- docs/modules/webapp-comply-sector.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/comply1xx/**
  reason: narrow the broad comply1xx glob to this leaf's own sector/ subdir (siblings
    T-5372/T-5373 own privacy/ and gdpr/); add the standard test-file and frob:doc
    doc companions
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/comply1xx/sector/**
  reason: narrow the broad comply1xx glob to this leaf's own sector/ subdir (siblings
    T-5372/T-5373 own privacy/ and gdpr/); add the standard test-file and frob:doc
    doc companions
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webapp_comply_sector.py
  reason: narrow the broad comply1xx glob to this leaf's own sector/ subdir (siblings
    T-5372/T-5373 own privacy/ and gdpr/); add the standard test-file and frob:doc
    doc companions
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-comply-sector.md
  reason: narrow the broad comply1xx glob to this leaf's own sector/ subdir (siblings
    T-5372/T-5373 own privacy/ and gdpr/); add the standard test-file and frob:doc
    doc companions
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply117_positive-COMPLY117-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply117_negative-COMPLY117-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply118_positive-COMPLY118-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply118_negative-COMPLY118-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply119_positive-COMPLY119-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply119_negative-COMPLY119-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply120_positive-COMPLY120-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply120_negative-COMPLY120-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply121_positive-COMPLY121-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply121_negative-COMPLY121-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply122_positive-COMPLY122-True]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_fixture[comply122_negative-COMPLY122-False]
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_findings_no_flags_must_stay_quiet
- tests/unit/test_webapp_comply_sector.py::test_comply_sector_flags_any_set
- tests/unit/test_webapp_comply_sector.py::test_websec_findings_hook_emits_gate_violation
- tests/unit/test_webapp_comply_sector.py::test_websec_findings_hook_empty_frameworks_short_circuits
- tests/unit/test_webapp_comply_sector.py::test_taint_gate_discovers_websec_comply_sector_hook
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
All applicability-flag-gated per the corpus (financial_institution=true, directed_to_children=true) -- ship as config-driven rules reading a [comply] table in frob.toml the repo opts into, never inferred. Fixture: frob.toml fixture with each flag set.