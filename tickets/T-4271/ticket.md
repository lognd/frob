---
id: T-4271
title: T-3799's whole-file scope claim on frob.lock blocks concurrent frob ack from
  other tickets
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3799/ticket.md
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: the ticket's stated fix (frob.lock's whole-file scope claim blocking concurrent
    frob ack) requires an entry-aware disjoint-edit narrowing in _check_cross_ticket_leakage's
    byte-level _sibling_branch_touched_path/_drop_hits_other_branch_never_touched
    machinery in _land.py; tickets/T-3799/ticket.md alone cannot hold this fix since
    T-3799 has live real (legitimate) uncommitted edits to frob.lock in its own worktree
    right now, so removing frob.lock from T-3799's own declared scope would break
    T-3799's own future SCOPE001 land check instead of fixing the real gap
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: the ticket's stated fix (frob.lock's whole-file scope claim blocking concurrent
    frob ack) requires an entry-aware disjoint-edit narrowing in _check_cross_ticket_leakage's
    byte-level _sibling_branch_touched_path/_drop_hits_other_branch_never_touched
    machinery in _land.py; tickets/T-3799/ticket.md alone cannot hold this fix since
    T-3799 has live real (legitimate) uncommitted edits to frob.lock in its own worktree
    right now, so removing frob.lock from T-3799's own declared scope would break
    T-3799's own future SCOPE001 land check instead of fixing the real gap
  actor: logan
  at: '2026-09-08'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_disjoint_frob_lock_ack_entries_do_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_colliding_frob_lock_ack_entry_still_refuses
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_disjoint_frob_lock_ack_entries_do_not_block
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while landing T-4264: T-3799 (in-progress, PATHEXT/shutil.which fix) declared 'frob.lock' as one of its own scope globs -- a whole-file exclusive lease on the repo's shared doc-ack digest lock. Any OTHER ticket's 'frob ack' (a routine DRIFT001 remedy, unrelated to T-3799's actual PATHEXT work) writes to frob.lock and trips gate:CROSSTICKET (CROSSTICKET001) against T-3799, even though the two tickets' frob.lock edits are disjoint entries in an additive JSON structure. T-4264 worked around it with --allow-cross-ticket since its own frob.lock diff (2 ack entries, both unrelated to gitio/PATHEXT) is genuinely disjoint from T-3799's. Suggest: frob.lock probably should not be scope-able as a whole-file lease at all (like tickets.md's LEDGER_PATH treatment), or CROSSTICKET should special-case frob.lock the way it already does other append-only/merge-friendly ledgers, since a shared lock file lease starves every OTHER ticket's routine ack work for the lease-holder's whole lifetime.