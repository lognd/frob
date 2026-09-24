---
id: T-5372
title: 'COMPLY101-108: privacy-policy page content, CCPA/CalOPPA'
state: in-progress
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
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5372
branch: t-5372
scope:
- src/frob/webapp/_comply_privacy.py
- tests/fixtures/webapp/comply1xx/privacy/**
- tests/unit/test_webapp_comply_privacy.py
- docs/modules/webapp-comply-privacy.md
- src/frob/gates/_taint_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/comply1xx/**
  reason: 'narrow to the privacy leaf: siblings own comply1xx/gdpr, comply1xx/sector,
    comply1xx/commerce; add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/comply1xx/privacy/**
  reason: 'narrow to the privacy leaf: siblings own comply1xx/gdpr, comply1xx/sector,
    comply1xx/commerce; add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webapp_comply_privacy.py
  reason: 'narrow to the privacy leaf: siblings own comply1xx/gdpr, comply1xx/sector,
    comply1xx/commerce; add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-comply-privacy.md
  reason: 'narrow to the privacy leaf: siblings own comply1xx/gdpr, comply1xx/sector,
    comply1xx/commerce; add this leaf''s own test+doc'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: widen taint_gate's WEBSEC hook-discovery prefix to also match _comply_ modules
    so this leaf's websec_findings-shaped hook is actually discovered, per T-5360
    doc defining no comply-specific hook convention yet
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: widen taint_gate's WEBSEC hook-discovery prefix to also match _comply_ modules
    so this leaf's websec_findings-shaped hook is actually discovered, per T-5360
    doc defining no comply-specific hook convention yet
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Required /privacy page + text-search for 'categories collected'/'effective date'/'do not track' sections (CalOPPA 22575(b)), 12-month-staleness lint on a frontmatter last_updated date (CCPA 1798.130(a)(5)), Do-Not-Sell link presence when a tracking pixel is detected (CCPA 1798.135(a)). Markdown/HTML content lint (regex/text-search, no grammar needed). Fixture: compliant and non-compliant privacy-policy pages.