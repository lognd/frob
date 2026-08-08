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

## Done report

Both confirmed-live halves fixed.

1. rapid-debt commit races DirtyMain outside the land lock: fixed via
`_commit_rapid_debt_only_drift` (src/frob/tickets/_land_git_ops.py),
following T-0793's uv.lock precedent -- auto-commits rapid-debt.jsonl
when it is the SOLE dirty path (unlike the uv.lock precedent, which
discards, this commits: the content is real and land-owned), then
`_refuse_if_main_dirty` re-evaluates before refusing.

2. DirtyMain misreads coordinator-owned dirt as a crashed land: fixed
via `_dirt_owned_by_no_open_ticket` (src/frob/tickets/_land.py) --
checks whether any dirty path falls inside any currently open
(queued/planned/in-progress/blocked) ticket's declared scope. When none
does, `_log_dirty_main_refusal` names the real cause explicitly instead
of the generic "has uncommitted changes" message that three agents this
session misread as a crashed land. Fail-closed on an unreadable ledger.

Split _log_dirty_main_refusal out of _refuse_if_main_dirty for
ARCH001. Land lock NOT widened, per the ticket's own explicit
instruction.

Scope correction: test file moved from tests/unit/test_rapid_sweep.py
(different module) to tests/test_ticket_land.py (where DirtyMain tests,
including the T-0793 precedent, already live).

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1699/ticket.md | 24 ++++++++++++++++++++++--
 1 file changed, 22 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_sole_rapid_debt_dirt_is_committed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_a_second_dirty_file_blocks_the_auto_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit::test_no_dirt_at_all_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_inside_an_open_tickets_scope_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_path_outside_every_open_tickets_scope_is_orphaned` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket::test_a_done_tickets_scope_does_not_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 2 error(s), 1094 warning(s), 731 waived
- error-findings: AFFECT001@src/frob/tickets/_land_git_ops.py, PRE001@tickets/T-1699
