---
id: T-1232
title: status/currency checks -- dated status/superseded-by header on audit docs,
  ticket-id prose vs ledger, index completeness
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/_docanchor.py
- docs/audits/docs-staleness-2026-07-29.md
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- docs/audits/README.md
- docs/audits/check-performance.md
- docs/audits/coordination-churn.md
- docs/audits/frob-blindspots-2026-07-23.md
- docs/audits/gates-accounting.md
- docs/audits/gates-quality.md
- docs/audits/gates-vacuous.md
- docs/audits/graph.md
- docs/audits/lang-check-docs.md
- docs/audits/perf.md
- docs/audits/strata.md
- docs/audits/test005-zero-classification-t1418.md
- docs/audits/tickets-testing-round2.md
- docs/audits/tickets-testing.md
- docs/audits/vet.md
- tests/test_gates.py
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_waive.py
- src/frob/gates/_doclink_docanchor.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/audits/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docanchor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/README.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/check-performance.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/coordination-churn.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/frob-blindspots-2026-07-23.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/gates-accounting.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/gates-quality.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/gates-vacuous.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/graph.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/lang-check-docs.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/perf.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/strata.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/test005-zero-classification-t1418.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/tickets-testing-round2.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/tickets-testing.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/vet.md
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1232: DOC009 gate wiring needs gates/__init__.py + check/__init__.py''s
    stage-group set touched; every existing docs/audits/*.md needs the new status
    header this ticket''s gate now requires'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1232: DOC009 must be registered in _KNOWN_GATE_RULES for waive-validation'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'T-1232: docstatus_gate (DOC009) lives here alongside doclink_gate/docanchor_gate'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1232: DOC009 needs a gates.md table row'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestDocstatusGate::test_missing_status_header_fires_doc009
- tests/test_gates.py::TestDocstatusGate::test_dated_status_header_passes
- tests/test_gates.py::TestDocstatusGate::test_superseded_header_with_missing_target_fires_doc009
- tests/test_gates.py::TestDocstatusGate::test_superseded_header_with_real_target_passes
designated_repro_test: null
threat: null
component: null
---
Require a dated status/superseded-by header on docs/audits/* (gate-checkable); check ticket-id prose against ledger state (open/closed/renumbered); check index completeness vs the docs tree. Ref: gate-gap class 6 in docs/audits/docs-staleness-2026-07-29.md.