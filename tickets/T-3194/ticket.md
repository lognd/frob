---
id: T-3194
title: T-3128's land-proof points at a code-empty commit; real fix landed via sibling
  T-3139's squash
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27, while assembling T-3157's ground-truth fixture suite.

T-3128's recorded land commit does not contain T-3128's code.

  git show --stat dac790e6e
    commit dac790e6e908644ebd2adbe57e3d426db1e54315
    fix(tickets): land T-3128 fleet_status reports a live registered
    worktree as a leaked lease

     CHANGELOG.md          | 1 +
     changelog.d/T-3128.md | 2 ++
     rapid-debt.jsonl      | 2 ++
     3 files changed, 5 insertions(+)

Zero lines of scripts/fleet_status.py -- the file T-3128's own scope
declared and whose behavior the ticket fixes. The actual code (the
`elif not _worktree_started_ticket_ids(path): matched =
_worktree_matches_ticket_by_scope_only(...)` discriminator branch in
`worktrees_touching_ticket`) is present on main, but was introduced by a
DIFFERENT ticket's land commit:

  git log -S "T-3128: a worktree can ALSO carry" --oneline -- scripts/fleet_status.py
    6f04de4c8 fix(tickets): land T-3139 frob ops process reap and
    fleet_status disagree about orphaned forkservers

T-3128 and T-3139 shared a worktree and landed sequentially; T-3139's
land commit squashed BOTH tickets' code changes into one commit, while
T-3128's own `frob ticket land` invocation recorded only the release-
artifact files it happened to touch (CHANGELOG.md, changelog.d/T-3128.md,
rapid-debt.jsonl) as ITS land commit's content.

WHY THIS MATTERS. Land-proof / verified=True is meant to assert "this
commit contains this ticket's code" -- ancestry evidence for what
actually shipped. Here it asserts that from the commit simply being
reachable / recorded as the land point, not from the commit's own
content. `git show --stat` on the recorded land commit shows the claim is
false: dac790e6e is reachable, is recorded as T-3128's land, and contains
none of T-3128's code. Any downstream consumer that trusts "T-3128 is
done, landed at dac790e6e" to mean "T-3128's diff is in dac790e6e" (a
revert-to-this-commit operation, a bisect, an audit reading `git show
<land_commit>` to see what a ticket did) gets the wrong answer -- the
real diff is one commit later, attributed to a different ticket id.

Concretely found via T-3157: building a must-fire ground-truth fixture
against T-3128's OWN parent commit (dac790e6e^) reproduced nothing --
the code that should have been introduced there already existed, because
it landed with the sibling instead. The true parent commit for T-3128's
fix is 6f04de4c8^ (= 4da2a85c2), not dac790e6e^.

TRIGGER (as best determined without deep-diving frob internals, which is
out of this ticket's scope): two tickets sharing one worktree, landed
sequentially in the same land session/squash. The second land's squash
folds in the first ticket's still-uncommitted-to-main code alongside its
own, but the FIRST ticket's own `frob ticket land` invocation (which ran
earlier and presumably found nothing new to commit, or committed only
its own release-artifact bookkeeping) still recorded a land_commit
pointing at whatever it produced.

SCOPE NOTE: this ticket is diagnosis + evidence only, per the reporting
agent's own instruction not to fix it in-series. The concrete instance
(T-3128 -> dac790e6e, real code in 6f04de4c8) is provided as a positive
control for whoever picks this up: the fix must make land-proof
verification for T-3128 either point at 6f04de4c8, or explicitly flag
dac790e6e as a code-empty land needing reattribution, and must not
regress the ordinary single-ticket-per-worktree case.
