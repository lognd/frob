---
id: T-3317
title: DOC006 flags every forward reference in design-first docs; evaluate a frob:planned
  marker
state: queued
kind: docs
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-020). This is an
IDEA/friction, not a confirmed bug -- filed as such; do not treat the
suggested mechanism as a spec, evaluate it.

Planning documents (subsystem designs, an invariant plan, ADRs) legitimately
name modules and tests that WILL exist once a ticket lands. DOC006 flags
each forward reference as "not a tracked file" (the reporter counted ~60
findings in one design doc). The only remedy today is a per-pointer inline
waiver citing the creating ticket -- workable (and this repo's own
unnecessary-waiver detector cleans these up once the paths land), but
expensive for design-first docs written before any code exists.

SUGGESTION TO EVALUATE, not a mandate: a `<!-- frob:planned T-#### -->`
section marker (or reuse `frob:until`) that scopes DOC006 to "must exist
once T-#### is done" for everything under that marker, replacing N
per-pointer waivers with one section-level declaration.

WHAT TO BUILD: evaluate the suggestion against DOC006's actual detection
mechanism (does it already have any section/until concept to extend, or
does this need new DSL surface). If a section marker is the right shape,
build it; if a different mechanism fits DOC006's existing design better,
build that instead and say why in the Done report. If, after review, the
existing per-pointer waiver is judged to be actually fine and this is not
worth building, say so plainly and drop the ticket rather than force a
change nobody needs.

MUST-FIRE FIXTURE: a genuine dangling reference to a path with NO creating
ticket at all, or citing a ticket that is already done and the path still
does not exist -- DOC006 must still fire.

MUST-STAY-QUIET FIXTURE: a forward reference under a `frob:planned T-####`
section (or whatever mechanism is built) where T-#### is open -- 0 DOC006
findings without a separate waiver per pointer.
