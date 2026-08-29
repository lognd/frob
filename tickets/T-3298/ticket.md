---
id: T-3298
title: SCOPE001 has no exemption for paths frob itself writes as a side effect
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/tickets/_scope.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-025, F-035, and the
second F-045 entry -- the repo's FROBLEMS.md has two headings numbered F-045;
this covers "frob ticket new inside a ticket trips that ticket's SCOPE001",
the duplicate/renumbered one).

CONFIRMED IN CODE: SCOPE001 (src/frob/gates/__init__.py, search "SCOPE001")
and the scope-lease path (src/frob/tickets/_scope.py) carry no exemption
list for paths frob itself writes as a side effect of routine ticket verbs.
`git grep -n "tickets/\*\*\|frob-managed\|_SCOPE_EXEMPT" src/frob/gates/`
returns nothing relevant to this class.

THREE REPORTS, same shape: a normal, DOCUMENTED workflow step writes a
frob-managed tracked file, and the very next `frob check --ticket` on the
SAME ticket flags that write as SCOPE001 (outside declared scope):
  - F-035 / F-045(dup): the implementer workflow explicitly says "file an
    out-of-scope discovery with `frob ticket new`" from inside a ticket's
    scope; doing so writes tickets/<new-id>/ticket.md, which
    `frob check --ticket <filing-id>` immediately reports as SCOPE001.
  - F-025 (broader): the same shape recurs for `--stamp-coverage`'s rewrite
    of frob-coverage.lock.json (see the coverage-lock cluster ticket -- do
    not duplicate that fix here, but the EXEMPT-LIST mechanism this ticket
    builds is what that one should plug into) and for tickets/T-*/ticket.md
    generally, i.e. every ticket ends up manually declaring
    frob-coverage.lock.json and tickets/** in its own scope just to stop
    the gate complaining about frob's own bookkeeping.

WHAT NOT TO DO: do not grant a blanket "tickets/** is always in scope for
everyone" exemption without attribution -- that would also silence a
genuinely out-of-scope EDIT to another ticket's ticket.md (e.g. hand-editing
someone else's ticket, which this repo has a standing rule against). The
exemption must be "the ticket that CREATED this ticket/wrote this file may
touch it", not "this path is nobody's business."

WHAT TO BUILD: SCOPE001 should recognize, and exempt, writes a ticket verb
itself performs as a side effect of the FILING ticket's own action:
  - tickets/<new-id>/ticket.md is exempt for the ticket that ran
    `frob ticket new` to create it (the scope_changes/creation audit trail
    already records this parentage per T-3271's Done-report note pattern;
    reuse it rather than inventing a second provenance mechanism).
  - Coordinate with the coverage-lock ticket filed alongside this one for
    frob-coverage.lock.json specifically -- that ticket may resolve its
    case a different way (per-ticket lock, or non-leased entirely); do not
    duplicate that fix here, just make sure this ticket's exemption
    mechanism is reusable by it if it wants a SCOPE001 exemption too.

MUST-FIRE FIXTURE: ticket A (scope excludes tickets/**) runs
`frob ticket new` to file ticket B as an out-of-scope discovery, then
`frob check --ticket A` -- must be 0 SCOPE001 findings for tickets/B/ticket.md.

MUST-STAY-QUIET (i.e. must still fire) FIXTURE: ticket A directly hand-edits
tickets/C/ticket.md (a ticket it did not create and has no declared scope
over) -- SCOPE001 must still fire; the exemption is provenance-scoped, not a
blanket allow on the tickets/ directory.
