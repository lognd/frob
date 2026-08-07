---
id: T-1209
title: 'perf: pii_structural ~8 independent ast.walk passes per file -- single bucketed
  NodeIndex'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
designated_repro_test: null
acceptance:
- text: 'GIVEN _scan_one_python_file dispatches to 8 sub-scans (_scan_python_ddl,
    _keywords.py keyword sweep, _python_fields.py orm columns/fields, _emails.py,
    _env_access.py) each doing its own ast.walk (8.84M walk resumptions, 39.6M isinstance,
    78 pct of the gate) WHEN one walk buckets nodes by type into a per-file NodeIndex
    consumed by each sub-scan THEN pii_structural drops from 6.7s toward ~1.5-2s native
    (report candidate #4)'
  evidence:
  - tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
threat: null
component: null
---
Root cause: gates/_pii_structural/__init__.py:141 _scan_one_python_file does one ast.parse (good) but ~8 separate full ast.walk passes per file. Fix: one walk that buckets nodes (Assign/Call/ClassDef/Str/Attribute...) into a per-file NodeIndex; each sub-scan consumes its bucket instead of re-walking. Companion lint rule on the sibling PERF01x-detectors ticket: '>1 ast.walk(tree) over the same tree in one function family'.