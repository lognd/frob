---
id: T-2600
title: T-2450 scope is a single semicolon-joined glob string, not two scope entries
state: dropped
kind: bug
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
- tickets/T-2450/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tickets/**
  reason: narrow to the ticket's own directory instead of the whole tickets tree
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2450/**
  reason: narrow to the ticket's own directory instead of the whole tickets tree
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while re-measuring T-2593 (over-broad scope enforcement). T-2450's
declared scope is a single ticket-frontmatter scope entry containing a
literal semicolon joining two globs:

    'src/frob/verify/**;src/frob/app/ticket_runner/**'

instead of two separate scope entries. As stored, that string is not a
valid glob pattern frob's scope matcher can meaningfully evaluate as
"src/frob/verify/** OR src/frob/app/ticket_runner/**" -- it is one
malformed pattern. This is a data/CLI-parsing defect in how the scope was
recorded (likely a `--scope` invocation that passed one semicolon-joined
argument instead of two separate `--scope` values or `--add` calls), not
an enforcement gap: large_glob_warnings/TICK009 correctly has nothing
sensible to say about a pattern that cannot be interpreted as a directory
glob in the first place.

Two things worth checking together:
1. Whether `frob ticket scope`/`new --scope` should validate/reject a
   semicolon (or other glob-illegal separator) inside a single scope
   entry at write time, rather than silently storing it.
2. T-2450's own scope should be split into two proper entries once
   someone picks it up (do not bulk-fix this from outside T-2450's own
   scope -- same over-broad-claim problem T-2593 was about).

## Failure log
- 2026-08-20 attempt 1: Premise already resolved: T-2450's scope was already split into two proper entries (src/frob/verify/**, src/frob/app/ticket_runner/**) by a prior fix, T-2614, recorded in T-2450's own scope_changes on 2026-08-19 -- the semicolon-joined single-string form this ticket describes no longer exists on current main. Verified by reading tickets/T-2450/ticket.md directly. Nothing to fix; requeuing rather than forcing scope. The open sub-question (should frob ticket scope/new --scope validate/reject a semicolon at write time) remains unaddressed and is worth a separate ticket if not already tracked, but is outside this ticket's declared scope (tickets/T-2450/**).

## Drop reason
- 2026-08-21: already resolved: tickets/T-2450/ticket.md was split into two proper scope entries by T-2614 (2026-08-19); confirmed by direct read of the ticket file on main (2026-08-21) (absorbed by T-2614)
