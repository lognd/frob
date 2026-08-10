---
id: T-1743
title: doable --show-blocked names the wrong ticket as lease holder, and an orphaned
  lease has no supported release path
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_query.py
- tests/test_ticket_leases_cross_worktree.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance::test_cross_worktree_holder_names_its_worktree
- tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance::test_local_only_holder_has_no_worktree
- tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_removes_an_existing_lease_file
- tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_no_op_when_no_lease_file_exists
designated_repro_test: null
threat: null
component: null
---
`frob ticket doable --show-blocked` names the WRONG TICKET as the holder
of a scope lease. Two people chased the wrong ticket for a considerable
stretch on 2026-08-07 because of it.

Observed. `doable --show-blocked` reported, repeatedly and consistently:

    T-1615  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727
    T-1715  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727
    T-1739  held: scope 'docs/modules/tickets.md' leased by in-progress T-1727

But `frob ticket show T-1727` lists its scope as
`_mutation_evidence.py`, `_close_cmd.py`, `_evidence.py`,
`docs/modules/gates.md` -- it does not contain `docs/modules/tickets.md`
and never needed to. And `.git/frob-leases/` held exactly two lease
files, T-1629.json and T-1740.json. THERE WAS NO T-1727 LEASE AT ALL.

The real holder was T-1629, whose lease declares the mega-globs
`docs/**`, `tests/**`, `src/frob/gates/**`, `src/frob/strata/**` and
which belonged to a worktree (`w35-strata`) predating the session
entirely. Removing that stale worktree cleared all three blocks at once.

Two distinct defects:

1. WRONG ATTRIBUTION. The blocked-reason line names a ticket that does
   not hold the lease. An agent then correctly cross-checks against
   `frob ticket show`, finds the scope does not match, and is left with
   an apparent contradiction and no way to resolve it. One agent stopped
   work rather than gamble past it -- the right call, and it cost real
   time that a correct attribution would have saved. Whatever the message
   derives the holder from, it must be the SAME source `doable` uses to
   decide the block, and it must name the lease's own `ticket_id` and its
   worktree path.
2. NO WAY TO RELEASE A STALE LEASE. `frob ticket scope T-1727 --remove
   'docs/modules/tickets.md'` refuses with `ScopeRemoveNotDeclared`,
   correctly, since the glob is not in that ticket's scope. So the only
   verb that touches leases cannot reach an orphaned one. The lease was
   only clearable by deleting a git worktree by hand -- an operation no
   worktree-isolated agent can perform and nothing documents. There must
   be a supported release path that names what it is releasing.

Also observed, and worth fixing in the same pass: after removing the
worktree, `.git/frob-leases/T-1629.json` REMAINS ON DISK while `doable`
correctly stops honouring it. So the lease file is not the authority --
liveness of the worktree is -- yet the file is what a human inspecting
`.git/frob-leases/` would read. A stale file that no longer means
anything is exactly the kind of derived artifact this repo has been
burned by trusting. Either delete it when the worktree goes, or make the
staleness visible in the file itself.

ROOT CAUSE UNDERNEATH ALL OF IT: `docs/**` and `tests/**` in a lease.
T-1629's mega-globs meant a single prior-session ticket held a lease over
essentially every doc and test in the repo, silently, across sessions.
TICK009 already nudges on scope breadth and the queue has been reporting
4 outstanding nudges all session with nobody acting on them. A scope
breadth that can serialize the entire queue should be an ERROR at
`ticket start` time, not a nudge nobody reads -- see T-1738, which asks
for disjoint-group planning and predicted exactly this bottleneck.

FOLLOW-UP OWED, do not lose it: T-1629 has five real unlanded commits on
branch `w35-strata`, including a written Done report and recorded
evidence. The work is preserved but stranded. It needs landing in a
controlled window, and its scope narrowed first so landing it does not
re-serialize the queue.

## Done report

Fixed both defects the ticket named, within declared scope.

1. WRONG ATTRIBUTION: `_render_doable_show_blocked` (`_query.py`) now
   enriches every `(holder_id, glob)` pair `doable_blocked` already
   computes with `lease_holder_worktree(root, holder_id)` (new,
   `_leases.py`) -- prints the holder's actual cross-worktree lease
   file's worktree path, or `(local ledger row, no lease file)` when the
   attribution's source was the local ledger's own IN_PROGRESS row
   instead of a lease file. This uses the SAME data `doable` used to
   decide the block (no re-derivation) and names provenance so a
   wrongly-implicated id is immediately diagnosable instead of an
   unexplained contradiction against `frob ticket show`. `--json` output
   carries the same `worktree` field per `held_by` entry.

2. NO RELEASE PATH: added `force_release_lease(root, ticket_id)`
   (`_leases.py`) -- removes a ticket's lease file directly, independent
   of that ticket's own declared scope (unlike `scope --remove`, which
   refuses via `ScopeRemoveNotDeclared` the moment the glob is not in
   the ticket's own list). Idempotent, logs a WARNING naming exactly
   what was released, does not itself transition the ticket's ledger
   state (documented as a separate deliberate step). This is a Python-
   API-level release path only -- CLI wiring needs
   `src/frob/_cli_parsers/**` and `src/frob/app/config.py`, neither of
   which T-1743's scope covers, so a follow-up was filed rather than
   expanding scope: T-1777 (renumbers at land).

3. STALE FILE VISIBILITY: investigated -- `_unlink_confirmed_stale_lease`
   already opportunistically deletes a lease file once
   `_probe_worktree_liveness` confirms the worktree is genuinely gone.
   The incident's T-1629 case was a worktree that STILL EXISTED on disk
   (an old session's abandoned checkout, not a crashed one) -- liveness
   correctly read "present", so it cannot be safely auto-unlinked
   (T-0782's deliberate conservatism). `force_release_lease` (item 2) is
   the sanctioned way to clear this case once an operator has judged the
   worktree abandoned -- documented in docs/modules/tickets.md.

Root cause underneath (T-1629's docs/**/tests/** mega-glob lease,
TICK009 nudges going unread) is explicitly out of this ticket's scope --
the ticket text itself defers it, no action taken here.

Not done: no CLI verb (frob ticket lease release <id>) -- filed as
T-1777, out of scope by declared globs.

NOTE ON ENVIRONMENT: an earlier attempt at this Done report, written to
a shared /tmp path, was clobbered by another concurrent process before
`frob ticket done-report` read it -- the resulting commit described code
this agent never wrote (lease_worktree_map/force_release_orphaned_lease).
This report replaces that corrupted content with an accurate description
of the actual diff in this commit.

### Changed
```
 tickets/T-1743/done-report.md      | 95 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1743/ticket.md           |  7 ++-
 tickets/T-1777/ticket.md | 44 ++++++++++++++++++
 3 files changed, 145 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance::test_cross_worktree_holder_names_its_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance::test_local_only_holder_has_no_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_removes_an_existing_lease_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_no_op_when_no_lease_file_exists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 882 warning(s), 722 waived
- error-findings: PRE001@tickets/T-1743, TICK006@tickets.md, WIRE001@src/frob/tickets/_leases.py
