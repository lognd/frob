---
id: T-0349
title: 'structural PII/secrets: email-shape value detection, non-regex (family 4)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0349 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0349 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: T-0455 scope hygiene narrowed tests/** to tests/test_gates.py, the wrong
    mirrored path -- this family's actual test file (used as T-0207 predecessor's
    evidence) is tests/test_pii_structural_gate.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_accepts_plain_address
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_display_name_wrapped
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_no_tld_dot
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_obfuscated_at
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_plain_text
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_email_literal_fires
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_same_line_discharges
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_line_above_discharges
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_plain_string_literal_does_not_fire
designated_repro_test: null
threat: null
component: null
---
T-0207 follow-on: detect email-shaped string literals via a structural parse (email.utils.parseaddr / WHATWG algorithm semantics), explicitly not regex per the ticket body, with the T-0157 fake-marker escape. Deferred from T-0207's scope.