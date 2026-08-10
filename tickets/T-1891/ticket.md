---
id: T-1891
title: frob ticket new prints a DirtyMain --no-commit warning even when it DID commit
  the ledger
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_new_renumber.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_ticket_leases.py
  reason: the no-commit-warning condition and its two internal batching callers
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_without_no_commit_never_warns_dirty
- tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_with_no_commit_still_warns_dirty
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_with_warn_if_dirty_false_stays_silent
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, on main. Ran 'frob ticket new ...' with no --no-commit flag. It printed:

  WARNING: tickets: T-1890 ledger change left DIRTY by --no-commit -- this WILL DirtyMain-block every concurrent 'frob ticket land' ... Fix: git add tickets/T-1890 tickets.md && git commit ...

but it had ALREADY committed the change itself (commit 9ca6bba96, tree clean immediately after). The recommended remediation then failed with 'nothing to commit, working tree clean'.

WHY IT MATTERS. DirtyMain deadlock is one of this repo's most expensive known footguns, so this warning is one an operator is trained to act on instantly. Crying wolf on the clean path is worse than silence: it teaches coordinators to ignore the one message that actually matters, and it burns a redundant commit round-trip during a live multi-agent wave.

FIX. Gate the warning on the ACTUAL post-write worktree state (or on the --no-commit flag genuinely being set), not on an unconditional code path. Add a regression test asserting the warning is absent when 'ticket new' commits, and present when --no-commit is passed.