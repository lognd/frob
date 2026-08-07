---
id: T-1541
title: audit non-done-report free-text ledger entry points for marker-lookalike corruption
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: new behavior (sanitize_narrative_for_ledger wired onto new_ticket/drop_ticket/record_failure)
    needs marker-lookalike-corruption regression tests; ticket's own acceptance requires
    tests proving no free-text write path can corrupt the ledger
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: new behavior (sanitize_narrative_for_ledger wired onto new_ticket/drop_ticket/record_failure)
    needs marker-lookalike-corruption regression tests; ticket's own acceptance requires
    tests proving no free-text write path can corrupt the ledger
  actor: logan
  at: '2026-08-05'
- op: remove
  glob: tests/test_tickets_acceptance.py
  reason: amend_acceptance/remove_acceptance route reason/text into structured frontmatter
    fields (YAML-escaped, never raw body prose) -- confirmed safe by design, no test
    needed
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_tickets.py::TestNewTicket::test_marker_lookalike_body_line_is_defused
- tests/test_tickets.py::TestFailureLog::test_marker_lookalike_summary_line_is_defused
- tests/test_tickets.py::TestDropTicket::test_marker_lookalike_reason_line_is_defused
designated_repro_test: null
threat: null
component: null
---
T-1536 fixed the marker-lookalike ledger-corruption class specifically
for the Done-report why path (compose_done_report/sanitize_narrative_
for_ledger) and hardened write_ticket's single-mode splice with a
post-write reparse-and-refuse check. Other free-text entry points that
also end up embedded into a ticket's body/ledger text -- ticket new
--body-file/--acceptance-file, scope --reason-file, drop --reason,
review --findings-file -- were not audited or defused against the same
marker-lookalike-line class in this ticket (kept narrowly scoped to the
done-report path per the incident this ticket root-caused). Audit each
of those write paths for the same vulnerability and apply sanitize_
narrative_for_ledger (or an equivalent) wherever caller-authored free
text is spliced into ticket.body before a single-mode ledger write.