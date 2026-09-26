---
id: T-5373
title: 'COMPLY109-116: GDPR/international disclosures'
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
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5373
branch: t-5373
scope:
- tests/fixtures/webapp/comply1xx/gdpr/**
- src/frob/webapp/_comply_gdpr.py
- tests/unit/test_comply_gdpr.py
- docs/modules/webapp-comply-gdpr.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/comply1xx/**
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/webapp/_comply_international.py
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/comply1xx/gdpr/**
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/webapp/_comply_gdpr.py
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_comply_gdpr.py
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-comply-gdpr.md
  reason: per-ticket fixture subdir to avoid T-5372 lease collision; module renamed
    to _comply_gdpr.py per coordinator naming; scope test file + doc per playbook
    convention
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
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_comply_gdpr.py::test_taint_gate_discovers_comply_gdpr_hook
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply109_positive-COMPLY109-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply109_negative-COMPLY109-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply110_positive-COMPLY110-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply110_negative-COMPLY110-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply111_positive-COMPLY111-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply111_negative-COMPLY111-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply112_positive-COMPLY112-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply112_negative-COMPLY112-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply113_positive-COMPLY113-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply113_negative-COMPLY113-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply114_positive-COMPLY114-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply114_negative-COMPLY114-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply115_positive-COMPLY115-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply115_negative-COMPLY115-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply116_positive-COMPLY116-True]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_fixture[comply116_negative-COMPLY116-False]
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_no_framework_short_circuits
- tests/unit/test_comply_gdpr.py::test_comply_gdpr_findings_no_signal_short_circuits
- tests/unit/test_comply_gdpr.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_comply_gdpr.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DSAR SLA (GDPR Art.12(3), one month), Art.13 identity/legal-basis/retention text, right-to-erasure endpoint (Art.17), storage-limitation/TTL schema check (Art.5(1)(e)) -- reuses 5148-4's migration-scan helper for the PII-retention-TTL-column check rather than building a second migration parser -- encryption-at-rest config, breach-notification runbook presence, EU AI Act Art.50 chatbot-notice, CASL/TCPA consent capture. Fixture per rule id.