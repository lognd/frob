---
id: T-2573
title: 'Milestone sequencing: make a do-last ticket reachable and release deadlocks
  statically provable'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/milestone-sequencing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: epic tracking doc only; leaf tickets carry the real code/doc scope
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/milestone-sequencing.md
  reason: epic tracking doc only; leaf tickets carry the real code/doc scope
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`runs_last` is GLOBALLY scoped today. `_doable_candidates`
(src/frob/tickets/_doable.py) excludes a runs-last ticket while ANY other
non-runs-last ticket is non-terminal, and `_OPEN_STATES` deliberately
includes QUEUED. With 83+ queued tickets and new ones filed hourly,
T-1614 ("RUNS LAST: audit every frob:waive for cop-outs") is STRUCTURALLY
UNREACHABLE -- it can never become doable, and the rot alarm has fired on
it for 13+ days. That is the concrete bug this epic fixes: a do-last
ticket must mean "last within a release", not "last in all of history".

Verified against code before filing (2026-08-18):
- _doable_candidates/_other_open_tickets behave exactly as this epic
  assumes: a runs_last ticket is excluded from doable while
  _other_open_tickets is non-empty; fellow runs_last tickets are already
  excluded from that count (the sibling carve-out M4b must preserve).
- _doable_sort_key (src/frob/tickets/__init__.py) is exactly
  `(-PRIORITY_RANK[t.priority], t.created, t.id)`.
- Ticket (src/frob/tickets/_models.py) has
  model_config = ConfigDict(frozen=True, extra="allow") -- confirmed via
  the class docstring, which documents this as a deliberate forward-
  compatibility relaxation. The milestone field is safely additive; there
  is no migration cliff.
- No milestone concept exists anywhere in src/ today (grep confirmed
  clean, exit 0 / no hits).

Naming decision (already made, do not relitigate): the field is
`milestone`, NOT `version`. REL001 already uses manifest.version for the
package version; a ticket field named `version` would read as either the
release it ships in or the ledger schema version.

Scope relationship (already decided, do not relitigate): sprint is a
FREE-FORM, UNORDERED label (assign/show/velocity). Milestone is TOTALLY
ORDERED (semver). Sprint = when we worked; milestone = what ships
together. They stay orthogonal -- do not fold milestone into sprint and
do not deprecate sprint.

_done_transition_guard already forbids closing an epic over an open
descendant -- MILE002 (see M5) is that same rule projected onto
milestones.

Constraints that bind every child ticket below:
- Milestone NEVER blocks on its own -- it ORDERS. Only MILE001/MILE002
  turn a milestone relationship into an error. Do not let milestone
  become a second, weaker blocked_by.
- An unmilestoned OPEN ticket must fail loudly, never sort arbitrarily.
- Semver comparison must be a real ordered comparison, not a string
  compare: "1.10.0" > "1.9.0" must hold.

Children: M1 (base) -> M2, M3, M4, M4b, M5 (each blocked_by M1) -> M6
(blocked_by M1 and M2).