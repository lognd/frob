---
id: T-1486
title: 'docstatus follow-up: ticket-id prose vs ledger + docs index completeness'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/_doclink_docanchor.py
- docs/design/registry/check-coverage.yaml
- docs/audits/docs-staleness-2026-07-29.md
- tests/unit/gates/test_doc011.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_doc011.py
  reason: 'DOC011 (ticket-id prose vs ledger, T-1486) needs regression tests bound

    to the new docstatus_gate/doc011 additions. tests/test_gates.py (the

    existing gate-family test home) is leased by another in-progress

    ticket (T-1205), so this ticket adds a new dedicated test file instead

    of contending for that lease.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'New DOC011 gate rule (T-1486) must be registered in

    _KNOWN_GATE_RULES (src/frob/gates/_waive.py) -- the same static list

    DOC008/DOC009/DOC010 already appear in -- or known_gate_rule_ids()

    never reports it and the check-coverage registry exhaustiveness test

    fails. One-line addition, mechanical registration only.

    '
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_unknown_ticket_id_in_prose_fires_doc011
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_known_active_ticket_id_passes
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_fenced_code_block_is_not_flagged
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_inline_code_span_is_not_flagged
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_no_ledger_at_all_still_flags_prose_mentions
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_duplicate_mention_on_one_line_reported_once
designated_repro_test: null
threat: null
component: null
---
T-1232 landed DOC009 (dated status/superseded-by header on docs/audits/*.md,
gate-gap class 6's first sub-item). Its other two named checks are still
open, deliberately left as a follow-up rather than forced into that
land:

1. Ticket-id prose vs ledger: a T-#### mention in doc prose should be
   checked against tickets.md/tickets-archive.md -- flag a mention of an id
   that does not exist at all, or (harder) one whose state contradicts the
   prose (e.g. "tracked under T-0397" when T-0397 is closed/renumbered).
   Needs a real ledger read from a gate (frob.tickets._store or similar),
   not just a doc-tree scan.
2. Index completeness: docs/index.md's own link inventory should be
   checked against the full docs/** tree walk (a doc file that exists but
   is not named anywhere in the index is exactly DOC001's orphan case in
   spirit, but from the index's own completeness angle rather than the
   file's reachability angle -- worth checking whether this is fully
   subsumed by DOC001 or is a genuinely distinct gap before building a
   new rule).

Ref: gate-gap class 6 in docs/audits/docs-staleness-2026-07-29.md.