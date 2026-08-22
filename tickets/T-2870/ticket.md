---
id: T-2870
title: BUG002 ticket-body waiver regex silently ignores an unquoted/malformed reason=
  value
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
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
T-2857 mode 2 (unquoted `reason=` value silently not recognized by the
land-time BUG002 check) has a different root cause than modes 1/3/4, and it
lives entirely OUTSIDE `src/frob/graph/dsl.py`'s scope, so T-2857 could not
fix it.

`frob.gates._bug_repro._BUG002_WAIVER_RE` (`src/frob/gates/_bug_repro.py`)
scans a TICKET BODY's raw text directly with its own regex:

    _BUG002_WAIVER_RE = re.compile(r'frob:waive\s+BUG002\s+reason="([^"]*)"')

This is entirely independent of `frob.graph.dsl` -- it never goes through
`parse_directives`/`markdown_anchors`, has no `MalformedDirective` concept,
and has no "shape matched but did not parse" diagnostic at all. When an
agent writes `reason=` with an unquoted value (no `"` at all), this regex
simply does not match -- `finditer` yields nothing, whatever caller reads
this (verify at implementation time) treats it exactly like "no waiver
present", and BUG002 runs its normal check with zero indication that a
waiver was ATTEMPTED and silently not recognized.

Required shape (same class as T-2857): a `frob:waive BUG002` shape-match in
a ticket body whose `reason=` value fails to parse (unquoted, or an
unescaped internal quote breaking closure the same way T-2857 mode 1 does
for markdown) must produce a LOUD, LOCATED diagnostic -- naming the ticket
id and why the waiver was rejected -- never silent fall-through to "BUG002
runs as if no waiver exists".

Positive controls:
- A well-formed `frob:waive BUG002 reason="..."` in a ticket body must
  still suppress BUG002 exactly as today (there ARE live BUG002 waivers in
  this repo -- verify the count is unchanged).
- An unquoted or malformed `reason=` must be reported, not silently
  ignored.

See T-2857's Done report for the measured repro and how this was found.
