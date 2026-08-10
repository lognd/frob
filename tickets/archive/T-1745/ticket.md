---
id: T-1745
title: Detect a queued ticket whose described fix already landed outside the ticket
  workflow (false queue signal)
state: dropped
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_doable.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Observed 2026-08-07 (T-1587): the ticket described a v2 Done-report
visibility bug and sat `queued`, undispatched 48h against a 4h threshold,
flagged critical by the dispatch-alarm machinery. The actual production
fix was already on `main` -- committed directly (commit f08541dc,
2026-08-05) OUTSIDE the ticket workflow, never through `frob ticket
land`, and the ticket's own state was never updated to reflect it. An
agent dispatched onto T-1587 spent real budget re-verifying a fix that
had already shipped two days earlier, because nothing in the queue
signaled "the described defect may already be resolved."

This is a DIFFERENT defect class from T-1675 (already-landed detection
at LAND time, now unconditional via a `state: done` check on
`base_ref`): T-1675 catches a ticket that is BEING landed a second time
after its own `frob ticket land` already ran. This case is a ticket
that was NEVER landed through the workflow at all -- its code arrived on
main by a direct commit (a human `git commit` bypassing `frob ticket
land`/`close` entirely) -- so there is no ticket-state transition to
compare against, and T-1675's positive signal (ticket's own record
shows `state: done` on base_ref) never fires; the ticket's record
genuinely still says `queued` because nothing ever told it otherwise.

Work direction (not yet designed in detail): a `doable`/dispatch-time
check that, for a ticket whose declared `scope` globs are narrow enough
to be meaningful, diffs the current tree against the ticket's `blocked_
by`-free baseline (or greps for `frob:ticket <id>` directives already
present in the scoped files) and flags "this ticket's own directive
markers already exist in the current tree with no corresponding land
commit" as a `WARN`-severity dispatch alarm, distinct from and additive
to T-1675's own already-landed-at-land-time check. Needs its own design
pass -- the false-positive shape here (a ticket's scope legitimately
overlaps a LATER ticket's `frob:ticket` directive, or a draft residue
citation) needs the same "positive signal, not absence" discipline
T-1675 established, not a second inference-from-emptiness check.

## Drop reason
- 2026-08-07: exact duplicate title and subject, filed twice from the same finding (draft renumbering at land produced two entries). T-1744 is canonical (absorbed by T-1744)