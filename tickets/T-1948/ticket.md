---
id: T-1948
title: 'Detector gap: frob:ticket-anchored code with no done signal is invisible to
  T-1934''s unlanded-work detector'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_unlanded.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED against a real specimen (coordinator audit, 2026-08-10): worktree
.claude/worktrees/t1552-ledger-v2, branch t1552-ledger-v2, held 525 lines
of UNCOMMITTED, ticket-anchored T-1691 work (src/frob/verify/_bisect.py,
opens with a `frob` + `:ticket` + ` T-1691` directive comment, plus
tests/unit/verify/test_bisect.py)
while the ledger read T-1691 as `queued`. No done-report existed for
T-1691, and its `ticket.md` state was never `done`/`dropped` on that
branch either -- the coordinator committed it as 836430a9b (chore(verify):
preserve uncommitted T-1691 bisect work found by coordinator audit) purely
to survive a worktree sweep; it remains unlanded and unreviewed.

Ran `frob.tickets._unlanded._unlanded_findings_for_branch(root,
"t1552-ledger-v2")` directly against this branch: it correctly found 4
OTHER genuinely finished-but-unlanded tickets on the same branch (T-1238,
T-1778, T-1820, T-1831 -- all `signal='done-report'`, `state_on_main=
'queued'`), but did NOT report T-1691. Root cause: T-1934's detector keys
on a "finished signal" (a `done-report.md` file, or `ticket.md`'s own
`state:` reading `done`/`dropped`) -- T-1691 had neither. The only signal
that identified the T-1691 work as real, owned, in-flight code was that
same directive-comment (`frob` + `:ticket` + ` T-1691`) embedded in the
source file itself, a signal T-1934's detector never reads.

This is a DIFFERENT gap than T-1934's own scope (T-1934: "looks done on a
branch, not done on main" -- crash AFTER commit, BEFORE land). T-1691's
shape is closer to "a ticket's code exists and is ticket-anchored, but
the ticket's own ticket.md was never updated to reflect that work is
in flight or complete" -- possibly compounded by the work being
UNCOMMITTED for a time (a third, even earlier shape T-1934 explicitly
does not cover either: `frob worktree sweep`'s existing `kept:dirty` gate
is the mechanism for uncommitted work, not this detector).

Do not widen T-1934's own scope to cover this -- file separately. A
starting design sketch: scan committed+uncommitted worktree files for
`frob:ticket T-####` directives, cross-reference against that ticket's
OWN state (in-progress vs queued vs done), and flag a directive-anchored
ticket whose own ticket.md disagrees with the code that cites it (e.g.
`queued` while an anchored file exists) -- deliberately a different
signal than "done-report exists", since it would need to fire even
BEFORE a ticket looks finished.
