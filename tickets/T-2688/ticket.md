---
id: T-2688
title: 'Gate: refuse/warn when a diff deletes or renames a test cited as some ticket''s
  evidence'
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
- src/frob/gates/_coverage.py
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
Deleting or renaming a test silently orphans OTHER tickets' evidence
citations, and this is a KNOWN, expensive defect class -- it has
already accounted for 4 of 4 of the entire measured error floor in a
prior investigation this session (per this repo's own record), and
resurfaced again this session as COV003 findings against 6 closed
tickets (T-1397/T-1526/T-1688/T-2344/T-2348/T-2365 -- see the
companion ticket for the full per-ticket split). Every occurrence so
far has been discovered LATE, by an unrelated sweep, long after the
deleting change already landed -- by which point the six-way judgment
call of "rebind vs obsolete vs needs a new test" has to be made
retroactively, per ticket, often without full context on what the
original evidence was proving.

## The fix: a gate, not a habit

The durable fix is that the DELETER must be caught at delete time, not
discovered by a later sweep. Concretely: a `frob check` gate (or a
pre-commit/pre-land check) that scans every open AND closed ticket's
bound evidence node ids, cross-references them against the current
`pytest --collect-only` set, and refuses (or loudly warns, matching
this repo's established WARN-then-ERROR-on-opt-in posture elsewhere,
e.g. SYS107) when a diff is ABOUT to delete or rename a test that some
ticket's evidence still cites.

This is exactly the shape COV003 already checks for OPEN tickets at
close/land time (`frob.tickets._new_gate_rule_acceptance` and
similar) -- the gap is that CLOSED tickets' evidence is not checked
against a diff that is about to delete the cited node, only
discovered later by an unrelated repo-wide sweep. The check needs to
run on the DIFF (what is about to be deleted/renamed), not only as a
standing repo-wide scan, so the deleter sees the refusal in their own
land, not six tickets down the line.

## Positive controls, both directions (required before landing this)

- Deleting a test that IS cited by some ticket's evidence (open or
  closed) MUST fire the gate.
- Deleting an UNCITED test (the overwhelming majority of test
  deletions in a normal refactor) MUST NOT fire the gate -- this
  cannot become a blanket "no test may ever be deleted" tax on every
  ordinary test cleanup, or it will be waived into uselessness within
  a week the same way the 997-waiver anti-pattern this repo has
  already paid for once happened.

## Scope note

Filed as investigation/design work, not scoped to specific files yet
-- the right implementation point (a new gate module vs extending
COV003's existing logic to also scan closed tickets vs a pre-commit
hook) needs a short design pass before this is picked up.
