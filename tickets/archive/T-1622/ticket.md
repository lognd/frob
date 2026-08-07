---
id: T-1622
title: Tickets filed from a worktree get draft ids that never survive a land
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- tests/**
- docs/**
- src/frob/tickets/_provisional.py
- src/frob/tickets/_new_renumber.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_provisional.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: narrow the chronically-broad tests/**,docs/** globs to the specific files
    actually touched for T-1622's land-time-promotion verification
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: narrow the chronically-broad tests/**,docs/** globs to the specific files
    actually touched for T-1622's land-time-promotion verification
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report
designated_repro_test: null
threat: null
component: null
---
`frob ticket new` run inside a worktree allocates a T-draft-<hex> id rather than a real T-#### one, because real id allocation needs main's ledger. Those draft ids never survive a land: the ledger splice drops the draft block, and any Done report citing it becomes a phantom citation (TICK006).

Consequence, hit FOUR separate times on 2026-08-05: an agent files legitimate follow-up tickets while working, cites them honestly in its Done report, and the coordinator must then refile each one on main, swap every citation in the worktree ledger, and delete the local draft block by hand before the land will pass. It is pure toil, it is error-prone (a blanket string-swap once renamed the draft's own block instead of removing it), and it happens on nearly every dispatch that discovers follow-up work.

T-1544 already covers the CITATION side (a Tier-A auto-fix that refiles and renumbers phantom draft citations). This ticket is the ALLOCATION side, which is the root: make an id filed from a worktree real from the start.

Options to weigh, and the choice belongs in this ticket:
- Reserve id ranges per worktree, so a worktree can allocate a real id with no coordination.
- Allocate through the existing cross-worktree lease side-channel (frob.tickets._leases already has a shared, peer-writable directory and liveness probing -- the coordination substrate exists).
- Keep draft ids but make the LAND rewrite them to real ids automatically, citations included, so the toil disappears even if the draft mechanism stays.

Whichever is chosen, the acceptance is the same: an agent files a follow-up ticket from a worktree, lands its work, and neither the agent nor the coordinator has to touch the ledger by hand for the citation to be correct on main.