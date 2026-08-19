---
id: T-2574
title: 'M1: Ticket.milestone field, semver ordering, CLI surface'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: T-2573
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_filing.py
- src/frob/semver.py
- src/frob/cli/tickets.py
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
Add `milestone: str | None = None` to `Ticket` (src/frob/tickets/_models.py)
and the filing spec, plus a total order over milestone values via semver
comparison. Invalid milestone strings must be REFUSED at write time with a
clear error, not sorted arbitrarily at read time. Semver comparison must be
a real ordered comparison, not a string compare: "1.10.0" > "1.9.0" must
hold.

CLI surface:
- `frob ticket milestone <id> <value>` -- mirror `set_runs_last` in
  src/frob/tickets/_setters.py (same validate-then-write shape, same
  ledger-commit path).
- `--milestone` flag on `frob ticket new`.

Scope must stay narrow: model field + semver comparator + setter + CLI
parser wiring only. Explicitly OUT of scope: no changes to
_doable_candidates, _doable_sort_key, MILE00x gates, or REL001 -- those
are M2 through M6.

Milestone NEVER blocks on its own -- it ORDERS, nothing more, at this
stage. An unmilestoned OPEN ticket is fine for M1 (MILE003 in M2 is what
enforces the field is set). extra="allow" on Ticket (confirmed:
src/frob/tickets/_models.py, ConfigDict(frozen=True, extra="allow")) means
this field is safely additive -- no ledger migration needed.
