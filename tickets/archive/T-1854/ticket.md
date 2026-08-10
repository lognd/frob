---
id: T-1854
title: frob refactor rename's evidence-citation rewrite bypasses replace_evidence's
  audit trail (T-1546 follow-up)
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/refactor/_repointer.py
- src/frob/refactor/_transaction.py
- tests/test_refactor.py
- tickets/T-1617/ticket.md
- tickets/T-1885/ticket.md
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: The regression test for routing per-ticket evidence-citation rewrites through
    replace_evidence lives in tests/test_refactor.py alongside every other test this
    file already carries for scan_evidence_citations (T-1546 precedent).
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1617/ticket.md
  reason: These two tickets/ files are prior ledger-only commits already sitting on
    this branch (T-1617 drop and T-1885 filing, both completed earlier this
    session in response to coordinator direction) that will land together with T-1854
    rather than as a separate land.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1885/ticket.md
  reason: These two tickets/ files are prior ledger-only commits already sitting on
    this branch (T-1617 drop and T-1885 filing, both completed earlier this
    session in response to coordinator direction) that will land together with T-1854
    rather than as a separate land.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/commands/refactor.md
  reason: AFFECT001 requires the affects()-closure docs actually be touched when the
    bound code changes, not merely resolve; scan_evidence_citations/run_refactor both
    changed behavior (T-1854 routing) and their doc anchors need the update.
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_refactor.py::TestRepointer::test_ticket_id_from_ledger_path_active
- tests/test_refactor.py::TestRepointer::test_ticket_id_from_ledger_path_archived
- tests/test_refactor.py::TestRepointer::test_ticket_id_from_ledger_path_legacy_monofile_is_none
- tests/test_refactor.py::TestRepointer::test_evidence_citation_targets_matches_scan_inputs
- tests/test_refactor.py::TestRunRefactor::test_per_ticket_evidence_rewrite_routes_through_replace_evidence
- tests/test_refactor.py::TestRunRefactor::test_evidence_rewrite_not_in_structured_evidence_falls_back_to_raw_op
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up from T-1546: `scan_evidence_citations`
(src/frob/refactor/_repointer.py) now detects and rewrites a moved/
renamed symbol's evidence citation across both the legacy
tickets.md/tickets-archive.md monofiles and this repo's real per-ticket
tickets/<id>/ticket.md (+archive) files -- but the rewrite it performs
is a RAW TEXT SUBSTITUTION (a literal string replace of the old symref/
node id with the new one, written directly to the ticket file), not a
route through `frob.tickets._evidence.replace_evidence`'s accountable
`--reason`-required, `EvidenceChangeEntry`-audited path (T-1733).

This is the actual "offer/auto-apply the matching --replace rebind" T-1546's
own body asked for and that this ticket's own narrower fix did not build:
a `frob refactor rename` that silently rewrites a ticket's Evidence
citation currently leaves NO audit trail of the rebind -- exactly the
asymmetry T-1733 built `EvidenceChangeEntry` to close for a manual
`--replace`, bypassed entirely by this automated path.

Scope for the follow-up: route `scan_evidence_citations`'s ops through
`replace_evidence` (or a `RewriteOp`-compatible variant of it) instead of
a raw line-text substitution, recording a `reason` derived from the
refactor operation itself (e.g. "carried by frob refactor rename: <old>
-> <new>") so a reviewer sees the automated rebind exactly like a manual
one. Needs care: `replace_evidence` is single-ticket-scoped (loads one
ticket by id from a path); `scan_evidence_citations` currently operates
on raw ledger file TEXT with no ticket-id context -- extracting/passing
the ticket id per matched line is the real design work here.