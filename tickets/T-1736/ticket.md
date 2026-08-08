---
id: T-1736
title: Wire frob.verify.record_intent into the land-commit path so the verify queue
  actually gets entries
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
- tickets/T-1736/ticket.md
- tickets/T-1736/done-report.md
- tickets/T-1829/ticket.md
- tickets/T-1686/ticket.md
- tickets/T-1821/ticket.md
- rapid-debt.jsonl
- tests/unit/test_rapid_sweep.py
- src/frob/verify/_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: record_intent wiring needs a doc anchor (COV001/AFFECT001) and land-path
    integration tests (tests/test_ticket_land.py is _land.py's own test file); ticket's
    own directory files per the T-1768/T-1220/T-1694 SCOPE001 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_land.py
  reason: record_intent wiring needs a doc anchor (COV001/AFFECT001) and land-path
    integration tests (tests/test_ticket_land.py is _land.py's own test file); ticket's
    own directory files per the T-1768/T-1220/T-1694 SCOPE001 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1736/ticket.md
  reason: record_intent wiring needs a doc anchor (COV001/AFFECT001) and land-path
    integration tests (tests/test_ticket_land.py is _land.py's own test file); ticket's
    own directory files per the T-1768/T-1220/T-1694 SCOPE001 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1736/done-report.md
  reason: record_intent wiring needs a doc anchor (COV001/AFFECT001) and land-path
    integration tests (tests/test_ticket_land.py is _land.py's own test file); ticket's
    own directory files per the T-1768/T-1220/T-1694 SCOPE001 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1829/ticket.md
  reason: 'SCOPE001: this worktree branch''s own history (T-1791 land, T-1686 start/block,
    T-1829 filing) carries these files into the diff against main; adding
    to scope per the established SCOPE001 precedent rather than rewriting branch history'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1686/ticket.md
  reason: 'SCOPE001: this worktree branch''s own history (T-1791 land, T-1686 start/block,
    T-1829 filing) carries these files into the diff against main; adding
    to scope per the established SCOPE001 precedent rather than rewriting branch history'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1821/ticket.md
  reason: 'SCOPE001: this worktree branch''s own history (T-1791 land, T-1686 start/block,
    T-1829 filing) carries these files into the diff against main; adding
    to scope per the established SCOPE001 precedent rather than rewriting branch history'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: rapid-debt.jsonl
  reason: 'SCOPE001: this worktree branch''s own history (T-1791 land, T-1686 start/block,
    T-1829 filing) carries these files into the diff against main; adding
    to scope per the established SCOPE001 precedent rather than rewriting branch history'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'SCOPE001: this worktree branch''s own history (T-1791 land, T-1686 start/block,
    T-1829 filing) carries these files into the diff against main; adding
    to scope per the established SCOPE001 precedent rather than rewriting branch history'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/verify/_watermark.py
  reason: the WIRE001 waiver at _watermark.py:224 names T-1736 as its own follow_up
    tracker for the enqueue-side wiring gap this ticket closes; landing requires re-pointing/removing
    it
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_overlapping_hunk_matches_the_symbol
- tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_non_overlapping_hunk_matches_nothing
- tests/test_ticket_land.py::TestTouchedSymrefsForIntent::test_different_file_matches_nothing
- tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_dry_run_is_a_noop
- tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_real_land_records_an_intent_entry
- tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_no_resolvable_symbols_records_nothing
- tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit::test_diff_failure_is_logged_not_raised
designated_repro_test: null
threat: null
component: null
---
found while landing T-1688: frob.verify._watermark.record_intent has no real caller yet -- T-1687 built it foundation-only and T-1688's worker only drains/advances/compacts an existing queue, it never enqueues. Something at land-commit time (most likely src/frob/tickets/_land.py's post-land hook) needs to call record_intent with the landed commit sha and touched symrefs, or the coalescing worker never has anything to verify.