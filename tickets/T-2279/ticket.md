---
id: T-2279
title: 'COV002: _lifecycle.py and _land.py changed with no owning ticket (T-2268 triage)'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Both COV002 identities resolve (frob:ticket directive added, or an existing
    ticket's scope widened to cover the file) and no longer appear in an unscoped
    frob check
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2268 holding-ticket triage (2026-08-17): COV002 fired on these two files
in the unscoped floor with no owning ticket -- a changed symbol with
neither a `frob:ticket` edge to an open ticket nor an open ticket whose
scope covers the file. Filed to give these an honest owner per T-2268's
own acceptance (every listed finding ends up fixed or owned, none left
attributed solely to the holding ticket).

    COV002  src/frob/app/ticket_runner/_lifecycle.py
    COV002  src/frob/tickets/_land.py

`src/frob/tickets/_land.py` is under a live lease (T-2255) as of this
filing -- do not start this ticket until that lease clears; check
`frob ticket show T-2255` / fleet status first.

Fix: add a `frob:ticket <this-id>` directive to the flagged symbol(s), or
confirm an existing open ticket's scope should have covered the file and
widen it instead of adding a redundant directive.
