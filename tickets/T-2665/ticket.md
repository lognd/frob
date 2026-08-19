---
id: T-2665
title: lease-leak detector reports [LEAK] for a ticket whose worktree exists, inviting
  a destructive requeue
state: done
kind: bug
origin: human
created: '2026-08-19'
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
- frob.lock
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'Repro and positive-control tests both live in

    tests/unit/test_coordinator_scripts.py, alongside the fix in

    scripts/fleet_status.py -- the same file the ticket''s original scope

    already declared.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: frob.lock
  reason: 'frob.lock was updated by `frob ack scripts/fleet_status.py::worktrees_touching_ticket`,
    required to clear DRIFT001 on the symbol this ticket''s fix changed.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'DOC002 required real anchors for the two new ARCH001-split helper

    functions (_worktree_matches_ticket_by_scope_only,

    _worktree_matches_ticket_by_dual_correlation) added to

    scripts/fleet_status.py; this is the doc file those frob:doc directives

    point to.

    '
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a44f96e6061be5e09a31028b919bb1e19745223c
---
## Measured

    scripts/fleet_status.py   ->   T-2583 -> <no worktree>  [LEAK]

    git worktree list | grep 2583
    -> /home/logan/projects/frob/.claude/worktrees/t-2583  61b508c44 [t-2583]

The worktree EXISTS, on a correctly-named branch, with an agent actively
working in it (its ticket is `in-progress` and a live process is running
there). The `[LEAK]` verdict is wrong.

Note the sibling case resolves correctly in the same run:

    T-2635 -> t-2635   [live]      <- same `t-<id>` naming shape, resolves
    T-2583 -> <no worktree> [LEAK] <- does not

So it is not a naming-convention gap. The likely difference is the
`.git/frob-leases/*.json` file: `read_all_leases` opportunistically unlinks
a lease file once it believes the worktree is gone (this is the mechanism
T-2651 documented). If the lease file was unlinked and the fallback
worktree resolution then fails, the ticket reports as leaked despite having
a live worktree. Verify that before fixing rather than assuming it.

## Why this is worse than a cosmetic wrong line

A `[LEAK]` verdict invites exactly one action: `frob ticket requeue`, which
releases the lease and takes the ticket out of `in-progress`. Doing that to
a ticket an agent is ACTIVELY WORKING would strip its lease mid-flight and
desynchronise its state from the ledger.

I came within one command of doing this to T-2583 today, and only caught it
because the six-hour-old commit timestamp looked wrong enough to re-check
`git worktree list` by hand.

This is the inverse failure of the bug the detector was built for. T-2651
fixed under-reporting (a real leak invisible because leases were enumerated
from worktrees). Over-reporting is more dangerous than the original bug,
because the original was silent and this one prompts a destructive action.

## Fix

Resolve the worktree from the same authority the rest of the tool uses --
`git worktree list` / the worktree's branch name -- and report `[LEAK]`
only when that resolution genuinely finds nothing. A missing lease FILE
must not on its own imply a missing worktree; T-2651's own root-cause note
says those files are unlinked opportunistically and are not authoritative.

Consider whether `[LEAK]` should additionally require the ticket to have no
live process working in it, since that is the condition an operator
actually cares about.

## Positive controls, both directions -- and these must run against real git

T-2599 shipped a worktree classifier whose unit tests all passed while it
was wrong on real data (18 STRANDED where the truth was ~0), because its
fixtures never built the distinguishing case. T-2617 fixed that and added
`TestWorktreeContentClassificationLiveGit`, running unmocked against real
`git init`/`git worktree add`. Follow that precedent here.

- an in-progress ticket WITH a live worktree does NOT report `[LEAK]`,
  including when its lease file has been removed. This is the failing case
- an in-progress ticket with NO worktree DOES report `[LEAK]` -- T-2377's
  original shape, the reason the detector exists. Without this the fix is
  indistinguishable from deleting the check
- a queued ticket reports nothing either way