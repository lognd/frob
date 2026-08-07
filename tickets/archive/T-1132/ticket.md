---
id: T-1132
title: 'tickets: validate blocked_by/parent ids at write time; doctor scans for malformed
  edges'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/doctor.py
- tests/system/test_cli_doctor.py
- docs/guides/install.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'T-1132''s own acceptance criterion (refuse a malformed blocked_by entry
    AT WRITE TIME) cannot be met by the Ticket/TicketSpec field validators alone:
    frob ticket block''s CLI handler mutates an EXISTING ticket via model_copy(update=...),
    which pydantic never re-validates (model_copy is documented to skip validation
    entirely) -- the one CLI verb that writes blocked_by post-creation must validate
    --by by hand before writing, or the whole fix is bypassed by the single most direct
    repro of the T-0380 incident'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/doctor.py
  reason: T-1132's acceptance criterion explicitly requires 'frob doctor flags existing
    malformed edges in the ledger' -- doctor.py is the only home for that scan/report;
    its existing integration test is the natural place for coverage
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: T-1132's acceptance criterion explicitly requires 'frob doctor flags existing
    malformed edges in the ledger' -- doctor.py is the only home for that scan/report;
    its existing integration test is the natural place for coverage
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/install.md
  reason: doctor.py's new scan_malformed_ticket_edges/MalformedTicketEdge carry frob:doc
    docs/guides/install.md#malformed-ticket-edge-scan-t-1132, matching the doc-anchor
    convention every other DoctorReport field in this file already uses (native-extension/derived-state/mutate-journal
    sections)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: documented is_valid_ticket_ref and iter_raw_ledger_frontmatter in the public-api/storage-internals
    sections, plus a blocked_by field note, per playbook section 6 (update docs in
    the same change) and to satisfy AFFECT001/COV001 on the new symbols
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_empty_string_by
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_malformed_by
- tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_accepts_valid_by
- tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_refuses_empty_string_blocked_by
- tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_refuses_malformed_parent
- tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_accepts_well_formed_blocked_by_and_parent
- tests/test_tickets.py::TestIsValidTicketRef::test_accepts_final_id
- tests/test_tickets.py::TestIsValidTicketRef::test_accepts_draft_id
- tests/test_tickets.py::TestIsValidTicketRef::test_rejects_empty_string
- tests/test_tickets.py::TestIsValidTicketRef::test_rejects_malformed_id
- tests/test_tickets.py::TestIterRawLedgerFrontmatter::test_returns_raw_dict_per_ticket
- tests/test_tickets.py::TestIterRawLedgerFrontmatter::test_skips_malformed_yaml_block_without_raising
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_flags_empty_string_blocked_by
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_flags_malformed_parent
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_ignores_well_formed_edges
designated_repro_test: null
acceptance:
- text: GIVEN a ticket write with an empty-string or non-T-#### blocked_by/parent
    entry WHEN the verb runs THEN it refuses with a clear error; frob doctor flags
    existing malformed edges in the ledger
  evidence:
  - tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_empty_string_by
threat: null
component: null
---
T-0380 sat silently undoable for days because blocked_by contained an empty string alongside three real (done) blockers -- doable() treated it as an unresolvable blocker and nothing surfaced why. Schema validation at write time plus a doctor scan for the existing ledger.