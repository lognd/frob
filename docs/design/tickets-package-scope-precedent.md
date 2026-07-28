# `src/frob/tickets/**` broad-scope precedent (T-1145)

One sentence: a ticket whose own body genuinely spans the whole
`frob.tickets` package (a cross-family refactor, split, or redesign) may
declare `scope=['src/frob/tickets/**', ...]` without being treated as
under-scoped -- SCOPE002's per-symbol doc/test/private-helper closure
warnings against that glob are EXPECTED noise for this specific package
shape, not a signal the ticket under-declared its scope.

## Context

T-1125 (a draft-id prose rewrite) surfaced ~548 SCOPE002 "scope closure"
warnings (plus one promoted to ERROR) purely from declaring the package
glob `src/frob/tickets/**`. Investigation (T-1145, this document) found
the same finding count reproduces against `tickets/**`-scoped work
generally, independent of what any single ticket in the family actually
touches -- confirming the volume is a property of the glob against the
package's shape, not a defect introduced by T-1125's diff.

`frob.tickets`'s own test suite is intentionally split across many
`tests/test_tickets_*.py` files (organized by FEATURE -- priority,
tiers/sprint, organization, velocity, evidence, land, leases, ...) rather
than 1:1 with the package's internal module split (`_setters.py`,
`_doable.py`, `_archive.py`, ...). SCOPE002's `code-missing-test`/
`test-missing-code` directions (docs/modules/gates.md#scope002-t-0998)
compare a scoped code symbol's `frob:tests` target file against the
declared scope glob one file at a time -- against a package this wide,
with a test suite this deliberately fragmented, the glob-vs.-file
comparison produces a large, permanent baseline of findings no single
ticket can close without either (a) padding every ticket's scope with
every `tests/test_tickets_*.py` file in the repo (defeats the purpose of
a scope declaration -- it stops meaning anything), or (b) never using the
package glob at all, even for tickets whose work genuinely IS
package-wide.

## Decision

Two dispositions, chosen per ticket by what the ticket's OWN body claims,
not uniformly:

1. **A ticket whose plan is scoped to one or two families/files inside
   `frob.tickets`** (the common case -- most tickets in this lineage,
   e.g. T-1103/T-1122/T-1123/T-1151's own per-family extractions) MUST
   NOT use the bare `src/frob/tickets/**` glob. Declare the specific
   module(s) touched plus the specific `tests/test_tickets_*.py` file(s)
   that cover them (`frob ticket scope <id> --set 'src/frob/tickets/
   _setters.py' --set 'tests/test_tickets_organization.py' ...`) -- this
   is TICK009's "chronically over-broad glob" nudge working as intended,
   and narrowing scope this way is the correct response to it, not a
   waiver.

2. **A ticket whose plan is genuinely package-wide** (a cross-family
   redesign, a migration, or a residue-sweep ticket enumerating several
   remaining families in one body -- e.g. T-1136's ledger-v2 design, or
   T-1152 (T-1151's own residue ticket) covering the evidence/transition
   and done-report/review/drop/attach families plus `_land.py`'s split in
   one plan) MAY declare `src/frob/tickets/**` (optionally narrowed further
   with `tests/**` alongside it, as T-1136 does). SCOPE002's resulting
   volume of findings for that ticket is accepted, permanent debt for the
   DURATION of that ticket, not a defect to chase to zero -- SCOPE002 is
   already a WARN-severity nudge (docs/modules/gates.md#scope002-t-0998,
   "a nudge, not a hard block"), and this document is the standing
   record of why a package-wide ticket's WARN volume is expected rather
   than investigated fresh by whichever agent next picks up work in this
   family.

The one SCOPE002 finding T-1125 saw promoted to ERROR-severity locally
was a `--ticket`-scoped, in-terminal severity bump specific to that
run's own diff shape, not a standing promotion of the SCOPE002 rule
itself (docs/modules/gates.md's "Promotion state" section is still the
source of truth for any real rule-wide WARN->ERROR promotion; none has
landed for SCOPE002 as of this document).

## Applying this

Before filing or re-scoping a ticket under `frob.tickets`, check which
disposition applies:

- Touches one or two modules/families? Use disposition 1 -- narrow the
  scope glob to those files plus their covering test file(s).
- Touches (or enumerates a plan spanning) the whole package? Use
  disposition 2 -- the broad glob is legitimate; do not spend ticket
  budget trying to silence SCOPE002's resulting WARN volume.

As of this document, the queue's only two open tickets carrying the bare
`src/frob/tickets/**` glob are T-1136 (ledger v2 design/migration,
disposition 2 -- genuinely package-wide by its own acceptance criteria)
and T-1152 (T-1151's own follow-up residue ticket: the remaining
evidence/transition and done-report/review/drop/attach families plus the
`_land.py` split, disposition 2 -- a multi-family residue sweep, same
shape as T-1136). Neither needed re-scoping under disposition 1; no
open ticket at the time of this investigation was mis-declared.
