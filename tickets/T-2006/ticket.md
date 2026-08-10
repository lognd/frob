---
id: T-2006
title: T-1983's auto-drop only runs inside the next sweep, so a stale sweep ticket
  stays dispatchable until an unrelated land happens
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
FOLLOW-UP TO T-1983, NOT A DUPLICATE. T-1983 ("Sweep-filed tickets go
stale before anyone reads them") is DONE and its mechanism works. The
same failure recurred TWICE on 2026-08-10 anyway, because T-1983 closed
only half the window. Read T-1983 first; do not re-implement it.

WHAT T-1983 BUILT: `_close_resolved_sweep_tickets` /
`_maybe_drop_resolved_ticket` (`src/frob/app/ticket_runner/_rapid_sweep.py`,
called at :1308) diffs `vanished = baseline - fresh` and auto-drops
sweep-filed tickets whose identities no longer reproduce.

THE RESIDUAL GAP: that call site is INSIDE the sweep, and the sweep runs
only after a land. So a sweep-filed ticket is only re-verified when some
LATER, UNRELATED ticket happens to land. In the window between filing and
that next land -- which at 5-agent dispatch is exactly when the coordinator
reads `frob ticket doable` and dispatches -- the ticket is listed, doable,
and unverified.

MEASURED, both on 2026-08-10, both after T-1983 landed:
- T-2000 ("post-land sweep regression from T-1665: 1 new identity, 2
  findings"): findings were already fixed inside T-1665's own land. No
  later sweep had run, so the auto-drop never fired. Dropped BY HAND.
- T-1998 ("post-land sweep regression from T-1977: 5 new identities, 8
  findings"): misattributed (the identities were in T-1995's files, not
  T-1977's) AND mostly already fixed by T-2002 before anyone started it.
  It was DISPATCHED to an agent, which merged main and found the actual
  remaining work was ONE LINE (`git show 917ba8e92 --stat`:
  `src/frob/app/ticket_runner/_new.py | 1 +`). A full dispatch cycle for
  one line.

COST: one wasted dispatch plus one manual drop, in one hour, on top of a
mechanism specifically built to prevent this.

## Do not fix it this way
- Do NOT run a full sweep at `doable`/`start` time. The whole point of
  T-1684's deferred detached sweep is that the multi-minute check is OFF
  the critical path; putting it back on an interactive command re-creates
  the problem T-1684 solved. The recorded identities are (rule, file)
  pairs -- re-measuring just those is cheap and is what this needs.
- Do NOT fix it by making the sweep file fewer tickets, or by adding a
  confidence threshold. The sweep filing promptly is correct; the defect
  is that nothing re-checks between filing and reading.
- Do NOT fix it only at `frob ticket start`. The coordinator picks work
  from `frob ticket doable`, so a stale ticket that is merely refused at
  `start` has already cost the dispatch decision.
- Do NOT hand this to a playbook line telling agents to re-measure before
  starting a sweep ticket. T-1983 already proved the mechanism must be
  automatic; an agent following a rule is not an enforcement.

## Acceptance criteria
1. A test that FAILS FIRST: file a sweep ticket, resolve its findings via
   an unrelated commit WITHOUT running another sweep, and assert that
   `frob ticket doable` currently still lists it. Then assert it does not.
2. Re-verification is scoped to the ticket's own recorded (rule, file)
   identities via the existing `_parse_sweep_ticket_identities`, not a
   full-tree check, and its cost is REPORTED as a measured number.
3. A sweep ticket whose identities still reproduce is unaffected -- assert
   no over-dropping, with a case where exactly one of two identities has
   vanished (the ticket must survive, not be dropped).
