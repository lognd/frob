---
id: T-2548
title: frob ticket body <id> silently resurrects a full duplicate active-tree copy
  for an archived id
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2763b40134572826d0e35d7f2db13680cb551825
---
Found while working T-2366: frob ticket body T-1397 --append "..." --reason
"..." (T-1397 is archived, state=done, lives under tickets/archive/T-1397/)
did NOT edit the archived ticket.md in place, and did NOT refuse for lack
of --archived support (unlike frob ticket evidence --replace, which has an
explicit --archived flag for exactly this). Instead it silently created a
brand-new tickets/T-1397/ticket.md AND tickets/T-1397/done-report.md in the
ACTIVE tree -- a full copy of the archived ticket's frontmatter plus my
appended note, with the archived copy left untouched. This produced a
DuplicateId state (T-1397 present in both tickets/ and tickets/archive/)
that then blocked a completely unrelated frob ticket body T-1526 --append
call with "id(s) {'T-1397'} present in both active and archive".

Recovered by hand: git rm -r the erroneous tickets/T-1397/ (both files),
then hand-appended the intended note directly to tickets/archive/T-1397/
ticket.md's body text (verified with frob ticket show T-1397 afterward --
parses fine, state=done, archived, no duplicate).

Fix: frob ticket body should either (a) grow an --archived flag mirroring
frob ticket evidence --replace --archived and edit the archived file in
place, or (b) refuse outright for an archived-only id with a clear error
naming the missing --archived flag, the same shape evidence --replace
already has -- never silently materialize a duplicate active-tree copy.
Also worth a regression test proving id resolution for `body` treats
active-vs-archived the same way `evidence --replace` does.

## Failure log
- 2026-08-21 attempt 1: already fixed by T-2678: set_body routes archived-ticket writes through write_archived_ticket; positive-control tests TestSetBodyArchivedTicketRouting pass on this tip; no code change needed in scope

## Drop reason
- 2026-08-21: already fixed by T-2678: set_body routes archived-ticket writes through write_archived_ticket; TestSetBodyArchivedTicketRouting positive-control tests pass on this tip; no code change needed in scope (absorbed by T-2678)
