---
id: T-1536
title: 'ledger self-corruption: done-report section replacement can duplicate a foreign
  ticket block and break whole-store YAML load'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_defuses_marker_lookalike_line
- tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_unbalanced_fence_around_marker_lookalike_still_defused
- tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_no_marker_lookalike_line_passes_through_unchanged
- tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_defused_line_no_longer_matches_the_real_marker_pattern
- tests/unit/test_ticket_store.py::TestWriteTicket::test_marker_lookalike_body_line_refuses_write
- tests/unit/test_ticket_store.py::TestWriteTicket::test_ordinary_body_still_writes_clean
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_marker_lookalike_line_in_why_is_defused
designated_repro_test: null
threat: null
component: null
---
2026-08-05 ~00:55 in worktree t-1350: after done-report refreshes for T-1318/T-1350/T-1225, tickets.md held a DUPLICATE T-1315 anchor whose block body was T-1318's report text with no frontmatter -- the whole store refused to load (T-1315 frontmatter is not valid YAML), 155336 chars / 2605 lines of the ledger were inside the corrupt span, and land failed NotFound for every ticket. Repaired by deleting the corrupt duplicate span (real blocks below it were intact). Root-cause replace_done_report_section/write path for how a section write can (a) target a foreign ticket's region and (b) duplicate an anchor. Independent hardening regardless of root cause: every ledger write (write_ticket/done-report/splice) MUST re-parse the full ledger post-write and refuse to persist on any load failure or duplicate anchor -- fail loudly before the corruption is durable. Also raises priority of the ledger v2 final cutover (per-ticket files structurally eliminate the shared-file blast radius).