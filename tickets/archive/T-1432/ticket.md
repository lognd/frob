---
id: T-1432
title: ledger auto-commit sweeps pre-staged index content into its commit
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- tests/test_tickets_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/test_tickets_leases.py
  reason: 'typo at filing: the real test file is tests/test_ticket_leases.py (no plural
    s on tickets)'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'typo at filing: the real test file is tests/test_ticket_leases.py (no plural
    s on tickets)'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_tickets_leases.py
  reason: both tests/test_ticket_leases.py and tests/test_tickets_leases.py exist
    and cover _leases.py symbols; the regression test may land in either
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_pre_staged_unrelated_file_never_rides_along_into_the_commit
designated_repro_test: null
acceptance:
- text: GIVEN a checkout with an unrelated file staged WHEN commit_ticket_ledger_change
    commits a dirty tickets.md THEN the resulting commit touches only tickets.md and
    the unrelated file remains staged
  evidence:
  - tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_pre_staged_unrelated_file_never_rides_along_into_the_commit
threat: null
component: null
---
Root cause of T-1403's c2fd45da incident: _add_and_commit_tickets_md runs 'git add tickets.md' then a bare 'git commit -m <message>', which commits the WHOLE index. Anything already staged in the checkout (e.g. by a conflicted stash pop, which auto-stages merged-clean files) rides along into the ledger commit under an unrelated message. Fix: pathspec-limit the commit ('git commit -m <msg> -- tickets.md', i.e. --only semantics) so the ledger commit can never contain anything but tickets.md, and add a regression test that stages a sentinel file, runs commit_ticket_ledger_change, and asserts the sentinel stays staged and out of the commit. Applies to every caller funneling through this helper (commit_start_transition, commit_ticket_ledger_change for new/drop/fail).