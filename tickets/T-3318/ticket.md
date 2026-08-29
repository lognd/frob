---
id: T-3318
title: CPLACE001 2-line cap fights a wrapped waiver reason plus mandatory follow_up
  on 88-col lines
state: queued
kind: bug
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
- src/frob/gates/_comment_placement.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-049).

A `frob:waive WIRE001` whose `reason=` names more than one downstream
consumer does not fit in 88 columns on one line (this repo's own ruff line
length), so it must wrap -- and wrapping the reason plus the mandatory
`follow_up=` line is 3 logical lines of directive, which CPLACE001 then
flags as over its 2-line cap. The two rules leave roughly 45 usable
characters for a reason string, which is tight for a real explanation.

WHAT TO BUILD: either (a) CPLACE001 should count a backslash-continued
directive (the `\` line-continuation convention this repo already uses
elsewhere for long frob:tests directives, per the examples in tickets like
T-3284's own body) as ONE logical line rather than counting physical lines,
or (b) raise the cap to 3 if continuation-counting is not practical. Confirm
which is a smaller, safer change before picking.

MUST-FIRE FIXTURE: a genuinely excessive directive block (e.g. 5+ logical
lines) -- CPLACE001 must still fire.

MUST-STAY-QUIET FIXTURE: a `frob:waive` with a wrapped `reason=` plus
`follow_up=` that together need 3 physical lines but are 2 logical
directives -- 0 CPLACE001 findings.
