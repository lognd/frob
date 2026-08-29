---
id: T-3403
title: fleet_status reports a live worktree's lease as LEAKED, and a leak verdict
  is actionable
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- tests/unit/test_fleet_status*.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/fleet_status.py
  reason: the two required fixtures
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_fleet_status*.py
  reason: the two required fixtures
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'scope closure: fleet_status.py symbols carry frob:doc targets into this
    guide'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_freshly_started_worktree_with_no_scope_commit_yet_is_not_leaked
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
fleet_status.py reported T-3394's scope lease as LEAKED ("T-3394 -> <no
worktree>  [LEAK]") in the same run whose own WORKTREES section lists
`t-3394  last-commit 7m`. Both statements came from one invocation, so this is
not a race between two observations.

MEASURED 2026-08-29, immediately after the report:

    git worktree list | grep 3394
      /home/logan/projects/frob/.claude/worktrees/t-3394   67d18768b [t-3394]
    ls -d .claude/worktrees/t-3394
      .claude/worktrees/t-3394

The worktree exists, git knows about it, it is on branch t-3394, and Series EV
was actively working T-3394 at that moment with a commit 7 minutes old.

WHY THIS IS DANGEROUS, not cosmetic. A reported leaked lease is ACTIONABLE: the
documented coordinator response is to drop or force-release the holding ticket,
because a lease held with no worktree behind it blocks other agents from ever
taking those files. Acting on this report would have dropped a ticket a live
agent was mid-way through, destroying its work and requeueing it -- and a
requeue invalidates every pre-existing worktree's land (T-1914).

The prior known defect in this area is the OPPOSITE polarity: leases enumerated
from worktrees mean an in-progress ticket with no worktree is INVISIBLE. This
one is a false POSITIVE from the same subsystem, which suggests the lease->
worktree correspondence is computed by a different path than the WORKTREES
listing, and the two disagree. Find the two paths and make them one -- the
existing note says "leases are enumerated from worktrees", which cannot be true
of both sections here or they could not disagree.

LIKELY DIRECTION, to be confirmed not assumed: path-shape mismatch. This repo
has a documented history of absolute-vs-relative path identities silently
failing to match (116 frob:waive directives and quarantine disposal both hit
it). A lease recorded with one path shape and a worktree enumerated with another
would produce exactly this: present in one listing, unmatched in the other.
Check the actual key shapes on both sides before accepting that explanation.

MUST-FIRE FIXTURE:   an in-progress ticket whose worktree genuinely does not
                     exist is reported as a leak.
MUST-STAY-QUIET:     an in-progress ticket with a live worktree is NOT reported
                     as a leak, including when the worktree path is expressed in
                     the other path shape.

ACCEPTANCE
- The two disagreeing code paths named, with file:line.
- Unified so the leak verdict and the WORKTREES listing cannot contradict.
- Both fixtures committed. A leak detector that reports nothing is
  indistinguishable from one that stopped looking, so the must-fire fixture is
  not optional.