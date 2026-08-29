---
id: T-3312
title: frob fmt accepts only one path argument, but FMT001's hint implies a list
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
- src/frob/_cli_parsers/_core.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-030).

`frob fmt a.py b.py` exits with "unrecognized arguments" -- the CLI's
positional argument is a single `[path]`, not `nargs='+'`. Worse, the
FMT001 finding's own remediation hint reads as if you CAN pass the whole
flagged file list at once, which sends the user straight into this error.

WHAT TO BUILD: either widen `frob fmt` to accept N path arguments (confirm
this is a straightforward change to the underlying formatter invocation
before assuming so), or -- if one-at-a-time is intentional -- fix the
FMT001 hint text so it does not imply otherwise (e.g. show a loop, or a
single representative path with "...and N more, one at a time").

MUST-FIRE / MUST-STAY-QUIET: `frob fmt a.py b.py` either formats both (if
widened) or the FMT001 hint text no longer suggests it can.
