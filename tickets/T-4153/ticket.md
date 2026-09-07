---
id: T-4153
title: 'REF001: exempt ledger-v2 tickets/T-*/ticket.md and done-report.md'
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'SCOPE002: ref_gate''s existing frob:doc/frob:tests targets must be in-scope
    alongside the file being edited'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: 'SCOPE002: ref_gate''s existing frob:doc/frob:tests targets must be in-scope
    alongside the file being edited'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: docs/modules/gates.md
  reason: 'revert: docs/modules/gates.md is a giant shared doc, wrong direction for
    SCOPE002'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/gates/test_refs.py
  reason: 'revert: docs/modules/gates.md is a giant shared doc, wrong direction for
    SCOPE002'
  actor: logan
  at: '2026-09-07'
evidence:
- tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_ticket_md_is_exempt_with_no_declaration
- tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_done_report_md_is_exempt_with_no_declaration
- tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_archived_ticket_md_is_exempt_with_no_declaration
- tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_unrelated_file_in_ticket_dir_still_fires_ref001
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3931 (scaffold day-one gate noise). REF001 fires on
every tickets/T-*/ticket.md the moment "frob ticket new" creates the first
ticket in a v2-mode (sharded-ledger) project, and again on
tickets/T-*/done-report.md the moment "frob ticket done-report" writes it.
Frob's own ledger artifacts should never be REF findings -- this is the
same shape T-3249/T-3444 already fixed for ledger-v1's single root
tickets.md/tickets-archive.md via a hardcoded exemption in
_DEFAULT_ROOT_MANIFEST_EXEMPT.

FIX (drafted, reverted from T-3931 due to a lease conflict): add a
_is_ticket_ledger_v2_artifact(rel_path) check in src/frob/gates/_refs.py,
matching frob.tickets._store's own _V2_TICKET_GLOB shape:
  tickets/T-*/ticket.md
  tickets/T-*/done-report.md
  tickets/archive/T-*/ticket.md
  tickets/archive/T-*/done-report.md
via fnmatch.fnmatchcase, wired into _ref_gate_file_violations's early-out
condition alongside _DEFAULT_ROOT_MANIFEST_EXEMPT/_allowlist_covers/
_is_collectible_test_filename/_is_under_vendored_tree.

BLOCKED: src/frob/gates/_refs.py is currently leased by in-progress
T-4124 (fnmatch-against-path-glob normcase audit, which is itself
auditing _refs.py:384's fnmatchcase call -- the same function this fix
would sit beside). Start this once T-4124's lease frees; the draft fix
and its 4 test cases (must-fire withheld: no cases fire after the fix;
must-stay-quiet: unrelated file in a ticket dir still flags; third
fixture: archived ticket dir) are described above, ready to reapply.