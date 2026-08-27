---
id: T-3045
title: 'V-model H5: the UI/UX requirement has no design; CMD_EVIDENCE_ALLOWED_KINDS
  structurally forbids UX tickets from carrying non-pytest evidence'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- tests/test_tickets_cmd_evidence.py
- docs/modules/tickets.md
- src/frob/gates/__init__.py
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'H5 is a one-line frozenset membership fix (CMD_EVIDENCE_ALLOWED_KINDS

    excludes TicketKind.UX, structurally forbidding a UX-kind ticket -- which

    genuinely has no pytest surface, same as docs -- from ever closing).

    Scope is the frozenset''s definition plus its close/land/COV003 call sites''

    existing test coverage (must-fire twins already exist for the other

    excluded kinds; this adds the must-stay-quiet twin for UX) plus the one

    doc section that enumerates the allowed kinds.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: 'H5 is a one-line frozenset membership fix (CMD_EVIDENCE_ALLOWED_KINDS

    excludes TicketKind.UX, structurally forbidding a UX-kind ticket -- which

    genuinely has no pytest surface, same as docs -- from ever closing).

    Scope is the frozenset''s definition plus its close/land/COV003 call sites''

    existing test coverage (must-fire twins already exist for the other

    excluded kinds; this adds the must-stay-quiet twin for UX) plus the one

    doc section that enumerates the allowed kinds.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/tickets.md
  reason: 'H5 is a one-line frozenset membership fix (CMD_EVIDENCE_ALLOWED_KINDS

    excludes TicketKind.UX, structurally forbidding a UX-kind ticket -- which

    genuinely has no pytest surface, same as docs -- from ever closing).

    Scope is the frozenset''s definition plus its close/land/COV003 call sites''

    existing test coverage (must-fire twins already exist for the other

    excluded kinds; this adds the must-stay-quiet twin for UX) plus the one

    doc section that enumerates the allowed kinds.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Two docstrings (frob.gates.__init__.evidence_covers_scope,

    frob.tickets._evidence''s cmd-evidence helper) state the allowed-kinds set

    as "today just docs" in prose -- now factually wrong once UX joins the

    frozenset. Fixing the stale claim in the same change as the frozenset

    edit, not leaving misleading documentation live.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'Two docstrings (frob.gates.__init__.evidence_covers_scope,

    frob.tickets._evidence''s cmd-evidence helper) state the allowed-kinds set

    as "today just docs" in prose -- now factually wrong once UX joins the

    frozenset. Fixing the stale claim in the same change as the frozenset

    edit, not leaving misleading documentation live.

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_ux_kind_closes
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_ux_kind_ticket_failing_cmd_blocks_close
- tests/test_tickets_cmd_evidence.py::TestCov003CmdEvidence::test_ux_ticket_closed_via_evidence_cmd_is_gate_clean
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_accepts_ux_cmd_entry
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
