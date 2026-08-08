---
id: T-1699
title: rapid-debt commit races DirtyMain outside the land lock; DirtyMain misreads
  coordinator-owned dirt as a crashed land
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/unit/test_rapid_sweep.py
  reason: DirtyMain/_refuse_if_main_dirty tests already live in tests/test_ticket_land.py,
    not tests/unit/test_rapid_sweep.py
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_land.py
  reason: DirtyMain/_refuse_if_main_dirty tests already live in tests/test_ticket_land.py,
    not tests/unit/test_rapid_sweep.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_sole_rapid_debt_dirt_is_committed
- tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_a_second_dirty_file_blocks_the_auto_commit
- tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_no_dirt_at_all_is_a_noop
- tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_inside_an_open_tickets_scope_is_not_orphaned
- tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_outside_every_open_tickets_scope_is_orphaned
- tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_a_done_tickets_scope_does_not_count
designated_repro_test: null
threat: null
component: null
---
T-1698 stopped a rapid land from leaving root permanently dirty, but the
cleanup commit happens OUTSIDE the land lock, leaving a small race that
matters at three-plus concurrent agents.

Sequence. `land()` holds the ledger/land lock for its body and releases
it when it returns. `_land_core_finish_post_land` then calls
`spawn_deferred_post_land_sweep`, which appends the debt line and commits
it via `_commit_rapid_debt`. Between the append and that commit, root is
dirty and unlocked. A second agent whose land reaches
`_refuse_if_main_dirty` inside that window refuses with `DirtyMain` --
transient and self-clearing, but indistinguishable to the victim from the
permanent deadlock T-1698 just fixed, and agents are briefed to stop
after two failed attempts.

Preferred fix, following existing precedent rather than inventing a
mechanism: `_refuse_if_main_dirty` already tolerates one specific benign
dirty shape -- `_restore_lock_version_only_drift` auto-restores a
uv.lock frob-version-only flap and re-evaluates instead of refusing
(T-0793). Give `rapid-debt.jsonl`-only dirt the same treatment: when it
is the ONLY dirty path, commit it (it is land-owned and always
committable on its own) and re-evaluate, rather than refusing. Any other
dirt, or rapid-debt.jsonl alongside anything else, must still refuse
exactly as today.

Do NOT instead widen the land lock to cover the post-land phase: that
phase is deliberately outside it (T-1684 made the sweep detached
precisely so the lock is not held across a multi-minute verification),
and re-acquiring it would reintroduce the serialization the rapid work
removed.

Second, process-shaped defect from the same incident, worth fixing in
this ticket because it has the same root: THE COORDINATOR WORKING
IN-PLACE ON THE SHARED ROOT BLOCKS EVERY AGENT'S LAND. Three agents this
session each drove a ticket to closed, then burned their remaining budget
retrying a land that could not succeed while the coordinator held
uncommitted edits in `/home/logan/projects/frob`. None of them could fix
it: an agent is correctly forbidden from committing or stashing state it
does not own.

`frob ticket land` should detect this and say so: when root is dirty with
files that belong to NO open ticket's scope and no land is in flight,
the refusal should name that shape explicitly -- "root has uncommitted
work belonging to no in-flight land; whoever owns the root checkout must
commit or stash it" -- instead of the generic dirty-tree message that
sends an agent looking for a crashed land. Three separate agents this
session independently misdiagnosed it as "a crashed land left dirt",
which is the reading the current message invites.