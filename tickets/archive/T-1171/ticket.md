---
id: T-1171
title: 'arch: extract tickets/__init__.py done-report/review/drop/attach family +
  split _land.py -- T-1152 residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_organization.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_organization.py
  reason: TestMutateLabels moved with mutate_labels into _reporting.py; COV002 needs
    the tests bound to T-1171 too
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_tickets_organization.py::TestMutateLabels::test_add_and_remove_labels
- tests/test_tickets_organization.py::TestMutateLabels::test_empty_call_is_error
- tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_strips_duplicate_leading_heading_from_why
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_composes_and_writes_atomically
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_caller_never_touches_markdown
- tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed
- tests/test_tickets.py::TestFailureLog::test_appends_creates_section
- tests/test_tickets.py::TestDropTicket::test_drops_queued_ticket_with_reason
- tests/test_tickets.py::TestAttach::test_file_source_copies_and_records_sha256
- tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry
- tests/test_tickets_review.py::TestHasApprovedReviewForCommit::test_true_only_for_matching_approve
designated_repro_test: null
threat: null
component: null
---
T-1152 extracted ONE family (evidence/transition) out of
src/frob/tickets/__init__.py into src/frob/tickets/_evidence.py
(__init__.py: 2333 -> ~1250 lines). Remaining work from T-1152's own
original scope, not touched this dispatch:

- done-report/review/drop/attach family (brief_ticket, mutate_labels,
  record_review, attach, drop_ticket helpers, compose_done_report/
  set_done_report, record_failure) -- still in
  src/frob/tickets/__init__.py.
- src/frob/tickets/_land.py (4866 lines, untouched across T-1108/T-1122/
  T-1123/T-1151/T-1152) still needs its own split into cohesive
  preflight/merge-splice/verify/sweep submodules per T-1108's original
  plan, before LARGE001 stops flagging it.

Follow the same pattern each dispatch: one cohesive family per land,
private module re-exported from __init__ via explicit imports, zero
caller-visible behavior change, existing tests as the safety net, carry
frob:ticket/frob:doc/frob:tests directives verbatim, repoint
docs/modules/tickets.md's frob:describes anchors and any tests/*.py
frob:tests directives at the new module path, add frob:ticket edges to
any test class/method a directive-repoint touches (COV002), carry a
file-level INV006 split-module waiver (T-0585 calibration-batch
precedent) if the moved prose trips it, watch for tests that monkeypatch
a moved function via the PACKAGE attribute (tickets_mod.<name>) -- those
need a late `from frob.tickets import <name>` inside the moved function
body instead of a module-top-level binding (two such hazards hit T-1152:
write_ticket and the bare `subprocess` module object itself).