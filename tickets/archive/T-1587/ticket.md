---
id: T-1587
title: 'ledger v2: Done reports were invisible to every body-reading consumer'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_reporting.py
- tests/unit/test_ticket_store.py
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body
- tests/unit/test_ticket_store.py::TestV2FullLifecycleDoneReport::test_close_does_not_refuse_recent_report
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_second_call_replaces_first_report
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_caller_never_touches_markdown
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_unknown_ticket_is_not_found
designated_repro_test: null
threat: null
component: null
---
v2 stores the Done report in tickets/T-####/done-report.md for lock independence (write_done_report), and set_done_report's v2 branch deliberately leaves ticket.body untouched. But load_all's v2 branch parsed only ticket.md, so Ticket.body never carried the report -- while EVERY consumer reads it from body: close's substantive-report check (_evidence.py), evidence recovery from the report, TICK006 phantom-filing resolution (_tickets_gate.py), the land ledger merge's has_done_report comparisons (_land_ledger_merge.py), and recover_done_report_why.

Effect in any v2 repo: frob ticket close refuses a ticket whose Done report was written seconds earlier ('write a ## Done report heading'), TICK006 goes blind, and the land-side merge cannot tell which side has a report. Observed as MissingEvidence close failures in the suite.

Fixed by making the in-memory Ticket canonical: load_all/load_archive splice done-report.md back into body (_merge_sibling_done_report), write_ticket's v2 branch splits it back out so a load-modify-write round trip never duplicates it into ticket.md, set_done_report returns the merged ticket so its return value matches the next load, and the v2 index cache keys on sibling done-report.md mtimes too (otherwise a report write would not invalidate the cache, since it never touches ticket.md).

Follow-up worth considering: an integration test that runs the full new -> start -> evidence -> done-report -> close cycle against a v2 repo end to end. The unit layer missed this because each half was individually correct.