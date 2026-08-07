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