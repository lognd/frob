---
id: T-2642
title: changelog entries read as bug reports, not release notes
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_fragments.py
- src/frob/app/ticket_runner/_land_cmd.py
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
`frob.release._fragments.write_changelog_fragment` writes a CHANGELOG.md
bullet using the ticket TITLE (`f"{ticket_id}: {ticket.title}"`), and
this repo's filing conventions favor a PROBLEM-stated title ("frob cycle
reports a false CLEAN", "over-broad scope is disclosed but never
enforced"). Every generated changelog entry therefore reads as a bug
report, not a release note describing what changed.

T-2615 flagged this explicitly as a deliberate judgment call, not a
defect to silently half-fix inside its own single-file scope
(src/frob/release/_fragments.py). Decision recorded in T-2615's Done
report: leave title-as-entry as-is for now (a problem-stated title is a
serviceable release note for a bug fix), but track a genuine "what
changed" line as its own design change.

## Scope for this ticket

Investigate and decide (not necessarily implement in one pass):
- Add an optional, explicitly-authored "what changed" field a ticket
  can carry (set at done-report time, or a new --changelog-note flag
  on frob ticket done-report/close), used in place of the title
  when present, falling back to the title otherwise.
- OR: a template/heuristic that rewrites a problem-stated title into a
  past-tense change description at generation time (riskier -- likely
  to produce misleading text for tickets where the fix does not map
  cleanly onto the problem statement).

Prefer the first (explicit, author-controlled) over the second
(inferred) -- an inferred rewrite risks announcing a change that did
not actually happen, the same class of defect T-2615 just fixed for
dropped tickets.
