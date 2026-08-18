---
id: T-2547
title: CrossTicketLeakage matches a zero-scope ticket as covering an unrelated unclaimed
  file
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
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
Landing T-2524 (scope docs/guides/agent-playbook.md only) was refused by
CrossTicketLeakage:

  ERROR: land: T-2524 branch carries 1 file(s) covered by T-2374's own
  scope, and T-2374 is still open on main -- landing would silently ship
  T-2374's work ahead of its own close:
  ['tickets/T-2524/ticket.md (unclaimed)']

The flagged file is tickets/T-2524/ticket.md -- T-2524's OWN ticket
ledger file, changed only by ordinary lifecycle bookkeeping (state:
queued -> in-progress, evidence_scope, evidence). T-2374's ticket.md on
main shows scope=[] (an empty list -- it has not declared any scope at
all yet, state: queued). There is no way an empty scope legitimately
"covers" tickets/T-2524/ticket.md; this reads as the CrossTicketLeakage
attribution logic treating a ticket with an EMPTY/undeclared scope as a
catch-all match for any "(unclaimed)" file (a file not covered by the
landing ticket's own declared scope), rather than excluding zero-scope
tickets from matching at all -- the same failure shape this repo has
already named once: "an exemption matching the normal case disables the
guard" (T-1967 precedent).

Landed T-2524 with --allow-cross-ticket per its own documented escape
hatch ("a genuine false positive... not to wave through a real sibling
leak") since the flagged file is unambiguously T-2524's own bookkeeping,
not T-2374's work. Filing this so the false-positive is tracked rather
than silently repeated by the next ticket that happens to share an
"unclaimed" ticket.md path with a zero-scope open sibling.

Likely fix: CrossTicketLeakage's per-file attribution should never match
a ticket whose declared `scope` is empty/undeclared against an
"unclaimed" file -- an empty scope should mean "covers nothing" for this
check, not "covers everything not otherwise claimed."
