---
id: T-2747
title: fleet_status reports a live worktree as a leaked lease when the worktree is
  not named t-<id>
state: done
kind: bug
origin: human
created: '2026-08-20'
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
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/fleet_status.py
  reason: correlate lease-to-worktree structurally, not by directory name
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: correlate lease-to-worktree structurally, not by directory name
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'record two further false-LEAK instances and widen the root cause: a series
    worktree can only encode one ticket id, so name-based lease correlation fails
    for every sibling ticket it holds'
  actor: logan
  at: '2026-08-20'
  old_length: 2667
  new_length: 4285
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_non_conventionally_named_worktree_matches_via_start_transition
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_series_worktree_matches_sibling_ticket_via_start_transition
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty
- tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicket::test_true_when_start_transition_commit_present
- tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicket::test_false_when_absent
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_series_worktree_matches_sibling_ticket_via_start_transition
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured, 2026-08-20

`scripts/fleet_status.py` reported:

    LEASES 5 (3 live, 1 leaked, 0 blocked-open)
      T-2740 -> <no worktree>  [LEAK]

The worktree exists and is registered:

    $ ls -d .claude/worktrees/waive-liveness
    .claude/worktrees/waive-liveness
    $ git worktree list | grep waive
    /home/logan/projects/frob/.claude/worktrees/waive-liveness  7a65bf6a0 [agent/waive-liveness]

It also holds 26 unlanded commits of real work. So a LIVE worktree with a
live agent was reported as a leaked lease.

## Root cause

The correlation keys on the `t-<id>` worktree naming convention (T-2599's
fast path, adopted by T-2665). This worktree is named `waive-liveness`
after its subject rather than after its ticket id, so the fast path finds
nothing and the fallback correlation does not recover it.

Nothing in the tooling requires a worktree to be named `t-<id>`; agents
name them after the work. So the detector is correct only for a naming
convention it does not enforce.

## Why this is more than cosmetic

A false LEAK verdict is dangerous in the specific way an operator acts on
it. This session has treated genuine lease leaks as recoverable -- a
stranded in-progress ticket holding a file hostage gets its lease
reclaimed. Acting on THIS verdict would have reclaimed a lease from a
live agent with 26 commits of unlanded work, which is exactly the
destructive outcome the leak detector exists to enable safely.

It is also an inverted repeat of T-2665, which fixed the opposite
false positive (a lease-file-present ticket reported [LEAK] while its
worktree existed). That fix adopted the naming fast path; this is the
case the fast path cannot see.

## Required

Correlate a lease to its worktree by something structural -- the
worktree's checked-out BRANCH, its recorded ticket id, or the lease file
itself -- not by the worktree's directory NAME. If a naming convention is
genuinely required, enforce it at `frob ticket work` time rather than
assuming it at read time.

## Positive controls, both directions

- a ticket whose worktree is named anything other than `t-<id>` is
  reported LIVE, not leaked
- a genuinely leaked lease (in-progress, no worktree anywhere) is STILL
  reported LEAK -- without this the fix has removed the detector's purpose
- a `t-<id>`-named worktree keeps working exactly as today

## Note

Because I have been directing every agent to trust `fleet_status` as the
authoritative source for lands, leases and root cleanliness -- correctly,
since hand-rolled probes are worse -- a wrong verdict from it now
propagates further than it used to. Worth a pass over its other verdicts
for the same class of assumption.




## TWO MORE INSTANCES, and the naming assumption is worse than first described

Measured shortly after filing:

    LEASES 5 (1 live, 2 leaked, 0 blocked-open)
      T-2737 -> <no worktree>  [LEAK]
      T-2740 -> <no worktree>  [LEAK]

Both verdicts are FALSE. Both worktrees exist, are registered, and hold
substantial live work:

    .claude/worktrees/t2738-t2737   [t-2738]              27 unlanded commits
    .claude/worktrees/waive-liveness [agent/waive-liveness] 29 unlanded commits

T-2737's case is the more instructive one and widens the defect beyond
'custom worktree names'. That worktree IS named by convention -- it is
just named for T-2738, the OTHER ticket in the same series. An agent
working a series in one worktree can only encode one id in the directory
name, so every additional ticket it holds is unresolvable by a name-based
correlation. This is not an edge case; working a series in a single
worktree is the standard dispatch pattern here.

So the detector is wrong for at least three shapes:
  1. worktree named after the subject rather than a ticket id
  2. worktree named after ticket A while holding a lease for sibling B
  3. (by extension) any renamed or reused worktree

Acting on either verdict would have reclaimed a lease from a live agent
mid-series -- 27 and 29 commits respectively.

Note also that both tickets DO have a genuine, separate problem worth not
conflating with this one: their work is complete-but-unlanded on a branch.
That is real and is being chased. It is simply not what a LEAK verdict is
supposed to mean, and the verdict gave no way to tell the two apart.