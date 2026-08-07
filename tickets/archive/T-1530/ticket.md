---
id: T-1530
title: ticket list summary footer counts ledger state, not display_state (lease-aware);
  route/style via shared list formatting
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_ticket_list_summary.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: lease-aware footer fix surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/unit/test_ticket_list_summary.py
  reason: lease-aware footer fix surface
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_leased_queued_ticket_counts_as_in_progress
- tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state
- tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary
designated_repro_test: null
acceptance:
- text: GIVEN a ledger-queued ticket with a live worktree lease WHEN frob ticket list
    renders THEN the summary footer counts it in-progress (matching the [in-progress@worktree]
    row above it), state names route through the shared style_state helper gated by
    the same color detection as the rows, and all output flows through the module
    logger
  evidence:
  - tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_leased_queued_ticket_counts_as_in_progress
  - tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state
  - tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary
threat: null
component: null
---
T-1528's footer tallies t.state raw, but the list rows above it render display_state(t, root) which folds in live worktree leases -- a leased-but-ledger-queued ticket shows [in-progress@...] in the rows while the footer counts it queued, so the two disagree on the same screen. Fix: census display_state(t, root) so footer matches rows exactly. Also: footer/stats lines must go through the same logger + style helpers as the rows (dim/bold via frob.app._style with _stdout_color gating) so formatting is consistent. User-reported 2026-08-04.