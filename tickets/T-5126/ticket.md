---
id: T-5126
title: 'DOC006 refuses unrelated lands over cli pointers inside ticket bodies merged
  in from dev: skip tickets/** in DOC006 and exclude ledger files from T-3324 attribution'
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- src/frob/tickets/_land_squash.py
- tests/gates/test_docptr.py
- tests/tickets/test_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docptr.py
  reason: fix DOC006 tickets/** skip
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: exclude dev-merged ledger files from T-3324 attribution
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/gates/test_docptr.py
  reason: positive controls for DOC006 tickets/** skip
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/tickets/test_land_squash.py
  reason: positive control for T-3324 attribution exclusion
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: capture repro, plan, and scope-lease blocker found while filing per coordinator
    dispatch
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1967
evidence:
- tests/gates/test_docptr.py::TestDoc006TicketBodyCliPointerSkip::test_open_ticket_planned_cli_pointer_not_flagged
- tests/gates/test_docptr.py::TestDoc006TicketBodyCliPointerSkip::test_real_doc_cli_pointer_still_flagged
- tests/tickets/test_land_squash.py::test_dev_merged_ledger_file_excluded
- tests/tickets/test_land_squash.py::test_own_ledger_edit_after_merge_still_counted
designated_repro_test: tests/gates/test_docptr.py::TestDoc006TicketBodyCliPointerSkip::test_open_ticket_planned_cli_pointer_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Description:
DOC006 (src/frob/gates/_docptr.py) treats ticket bodies (tickets/**/ticket.md, done-report.md, tickets/archive/**) as documentation whose cli pointers must resolve. Ticket bodies are narrative and describe future or rejected CLI surface by design (e.g. 'frob sys split', 'frob doctor --whereis'), so DOC006 must skip them, or downgrade to WARN naming the ticket, never ERROR attributed to a land. Separately, the T-3324 attribution logic in src/frob/tickets/_land_squash.py counts ledger files merged in from dev as 'this land's own touched files', causing unrelated lands to be refused.

Repro (measured 2026-09-19): frob ticket land refused four times (T-4659 18:42/18:51, T-4416 19:29, T-4684 20:14) with: self-conformance finding(s) attributable to this land's own touched files (T-3324): DOC006: cli invocation pointer in tickets/T-####/ticket.md:NN does not resolve -- where the ticket body belonged to a DIFFERENT ticket that rode in via merge of dev, and the pointer was a planner's backticked planned/rejected CLI form.

Plan:
1. In src/frob/gates/_docptr.py, skip tickets/**/ticket.md, tickets/**/done-report.md, and tickets/archive/** from DOC006 cli-pointer resolution (or downgrade to WARN naming the owning ticket).
2. In src/frob/tickets/_land_squash.py, fix the T-3324 attribution helper so ledger files merged in from dev are excluded from 'this land's own touched files'.
3. Positive controls: (a) fixture ticket body with a backticked nonexistent command produces no DOC006 error; (b) a land whose merge brings in such a ticket file is not refused; (c) a real docs/*.md unresolved pointer still fires.

BLOCKED: src/frob/gates/_docptr.py is under live cross-worktree lease by T-4709 (docs narrative ticket) and src/frob/tickets/_land_squash.py is under live cross-worktree lease by T-4722 (docs narrative ticket); docs/modules/gates.md is leased by T-4693. This ticket cannot acquire scope on any of its three required files right now.

## Unblock log
- 2026-09-19: unblocked by T-4709 -- lease released
- 2026-09-19: unblocked by T-4722 -- lease released
- 2026-09-19: unblocked by T-4693 -- lease released