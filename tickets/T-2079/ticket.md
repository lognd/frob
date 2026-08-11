---
id: T-2079
title: 'Ledger ownership: refuse a main-side write to a leased tickets/T-#### path'
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1669 (which delivered only the PROMOTION half: allocator_lock
wired into finalize_draft/finalize_draft_for_land, T-1669's Done report).

The OWNERSHIP half of T-1669's original design, still undone: under v2
(one file per ticket, tickets/T-####/, confirmed migrated -- T-1631 is
done, no tickets.md monofile exists on main as of 2026-08-10), a ticket's
record should be writable only by the holder of its lease:
- a worktree holding T-1234's lease may write T-1234 and nothing else
- main must REFUSE to write a ticket currently leased to a worktree (the
  T-1617 incident: a kind field change on main was silently dropped by a
  later merge because main edited a ticket a worktree owned)
- a ticket with no lease is main's to write

T-1669's own text: "Enforcement under v2 is a path check: refuse a commit
touching tickets/T-####/ you do not hold."

Also worth folding in here or filing alongside: the citation-rewrite gap
measured while working T-1669-- `frob ticket renumber`/`_scan_v2_
reference_files` (src/frob/tickets/_renumber_v2.py) only rewrites
whole-word citations inside tickets/**/*.md (ticket.md/done-report.md)
plus code `frob:ticket` directives (`_scan_code_references`). Free-form
docstring prose outside that glob, and commit messages, are never
rewritten -- T-2060 today required hand-fixing stale prose citations
after a renumber for exactly this reason.
