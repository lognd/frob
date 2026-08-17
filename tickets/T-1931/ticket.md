---
id: T-1931
title: land's Tier-A auto-fix can silently re-add a file the CrossTicketLeakage guard
  just refused
state: dropped
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Observed live during T-1556's land (commit 16880d5170a2). T-1556's own
worktree diff added `may "env.read" via ".../_new.py";` to
design/frob.strata (the interface edge its own os.environ.get read
needed). design/frob.strata is T-1901's declared scope (T-1901 is
in-progress, open on main) -- `frob ticket land T-1556`'s own
CrossTicketLeakage guard correctly refused the first attempt on exactly
this file.

The line was then manually reverted in the worktree (a plain deletion,
committed) specifically to avoid landing T-1901's file as an undisclosed
passenger, and `frob ticket land T-1556` was re-run. It passed the
CrossTicketLeakage guard this time -- but `land`'s own pre-land Tier-A
auto-fix pass (`ticket land: T-1556 pre-land Tier-A fixes applied 2
fix(es)`) silently RE-ADDED the exact same line (an undeclared-capability-
effect auto-fixer reacting to the still-live `os.environ.get` call in
_new.py), and that auto-fixed state is what actually landed --
`design/frob.strata` shows the env.read edge present in the landed
commit, identical to what the guard refused minutes earlier.

The CrossTicketLeakage check evidently runs against the branch diff
BEFORE Tier-A auto-fix reintroduces the file, so a deliberate revert
performed specifically to satisfy that guard can be silently undone by
land's own later auto-fix step, and the passenger ships anyway with no
second guard check catching it. This defeats the guard's own purpose for
any file whose content a Tier-A fixer can regenerate deterministically
from surrounding source (design/frob.strata via the undeclared-capability
fixer is one concrete instance; there may be others).

Net effect here: T-1901's own file was carried onto main ahead of its own
close after all, just via a different mechanism than the one the guard
was built to catch.

## Drop reason
- 2026-08-09: Folded into T-1932's general fix per T-1932's own explicit sequencing request -- the same _reverify_cross_ticket_leakage_post_mutation change closes both; a standalone T-1931 patch would have been a redundant overlapping fix to the same guard, which both tickets explicitly warn against. See T-1932's Done report. (absorbed by T-1932)
