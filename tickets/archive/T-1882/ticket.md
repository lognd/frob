---
id: T-1882
title: frob ticket renumber with no arguments silently renumbers EVERY ticket, destroying
  the whole id space
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_renumber_v2.py
- src/frob/tickets/_new_renumber.py
- tests/system/test_cli_ticket.py
- tests/test_ticket_leases_cross_worktree.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'T-1882: renumber implementation and its CLI dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_renumber_v2.py
  reason: 'T-1882: renumber implementation and its CLI dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-1882: renumber implementation and its CLI dispatch'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/system/test_cli_ticket.py
  reason: T-1882's own new/updated test coverage for the destructive no-arg renumber
    removal and the T-1882 lease-conflict guard lives in these three existing test
    files
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: T-1882's own new/updated test coverage for the destructive no-arg renumber
    removal and the T-1882 lease-conflict guard lives in these three existing test
    files
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets.py
  reason: T-1882's own new/updated test coverage for the destructive no-arg renumber
    removal and the T-1882 lease-conflict guard lives in these three existing test
    files
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets.py::TestSchemaExtras::test_renumber_makes_ids_contiguous
- tests/test_tickets.py::TestSchemaExtras::test_renumber_rewrites_blocked_by
- tests/test_tickets.py::TestSchemaExtras::test_renumber_dry_run_previews_without_writing
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_refused_by_unmerged_sibling_worktrees_live_lease
- tests/test_ticket_leases_cross_worktree.py::TestRenumberRefusesLiveCrossWorktreeLease::test_bulk_renumber_dry_run_still_works_under_a_live_lease
- tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved::test_no_args_always_refuses
- tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved::test_dry_run_still_previews_read_only
designated_repro_test: tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved::test_no_args_always_refuses
threat: null
component: null
anchor: false
anchor_reason: null
---
INCIDENT, 2026-08-08, coordinator. `frob check` reported one error:

  TICK002: draft id T-draft-5b2a5265 survived onto the default branch --
  finalize it: `frob ticket renumber T-draft-5b2a5265 <new>`

The obvious first attempt, `frob ticket renumber T-draft-5b2a5265`,
correctly refused ("requires both <old> and <new>, or neither"). The
refusal names a no-argument form. Running that no-argument form
renumbered EVERY ticket in the repo:

  renumbered 273 ticket(s)

All 273 `tickets/T-####/` directories were deleted and rewritten as
`tickets/T-0001/` .. `tickets/T-0273/`. Every ticket id in the queue
changed at once. Nothing was committed, so recovery was
`git checkout -- tickets/` plus removing the 273 untracked directories,
and the tree hash was confirmed identical to the pre-run state. Had this
been committed, or had any concurrent agent landed on top of it, the
damage would have been unrecoverable in practice: every lease file,
evidence citation, `blocked_by` edge, `frob:ticket` code directive, and
archived cross-reference points at an id by name.

WHY THIS IS CRITICAL. This is a single unguarded command, one word
shorter than the correct one, that rewrites the entire ledger's primary
key. It has no confirmation prompt, no dry-run, no `--force`, and no
summary of what it is about to do. The error message for the safe form
actively advertises it. This is the ledger-corruption class the whole
tool exists to prevent, reachable by a plausible typo.

REQUIREMENTS.

1. The no-argument form must not perform a destructive rewrite without
   explicit opt-in. Require `--all` (or equivalent) plus a confirmation,
   and print the count and the first/last few mappings BEFORE acting.
2. Add `--dry-run` printing the full old->new mapping and touching
   nothing.
3. If the no-argument form has no legitimate caller -- determine this,
   do not assume -- DELETE IT. Preferring deletion of a verb over adding
   a mechanism to manage it is this repo's standing policy, and a bulk
   id rewrite has no obvious honest use once ids are referenced from
   code, leases, and archived tickets.
4. Fix the refusal message so it does not advertise the destructive
   form. It should name only `renumber <old> <new>`.
5. Refuse any renumber while another worktree holds a live lease.
   Renumbering ids out from under five running agents corrupts every
   lease file by name.

RELATED. The draft reached main because a ticket-only change was
committed directly to the shared checkout rather than going through
`frob ticket land`, which is what finalises a draft id. That bypass is
worth its own look: either the direct-commit path should finalise
drafts too, or TICK002 should be the only supported way back and the
fix path must be safe. It currently is not.