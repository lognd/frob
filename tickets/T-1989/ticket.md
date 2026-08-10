---
id: T-1989
title: 'T-1968''s land regressed the floor 0 to 105: documentation describing directives
  now raises DSL001'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1968's land (`4d40d13a4455c29ed08b34c0893f17f5cec72269`) took the
unscoped error floor from 0 to 105. Every one is DSL001 from the new
"unhandled markdown directive" path, and the overwhelming majority are
DOCUMENTATION DESCRIBING DIRECTIVES, not directives anyone intended to
be live.

MEASURED, on main, immediately after that land:
  frob check --only gates -> gate:DSL 105 errors, gate-summary 105 errors
  (the floor was 0, verified by me after T-1970 landed and BEFORE T-1968)

Sample findings:
  CHANGELOG.md:1853        unhandled markdown directive (verb='waive')
  CHANGELOG.md:1917        unhandled markdown directive (verb='invariant')
  docs/commands/sys.md:139 unhandled markdown directive (verb='claims')
  docs/design/coding-performance-corpus.md:3   (verb='doc')
Worst files: docs/strata/surface.md (15), docs/guides/coordinator-scripts.md
(14), docs/strata/kernel.md (5), docs/strata/host.md (5),
docs/modules/gates.md (5), docs/strata/boundary.md (4).

A CHANGELOG entry recording that a waiver was added, and a command
reference page explaining what a verb does, are MENTIONS. Making them
hard errors is precisely the false-positive flood T-1968's own
investigation identified and set out to avoid.

MIS-ATTRIBUTION TO CORRECT: the landing agent reported these as
"pre-existing, unrelated background debt confirmed via git blame to
predate this work (earliest 2026-07-17)". That reasoning is invalid --
git blame dates when the MARKDOWN was written, not when the RULE began
reporting it. The text is old; the finding is new. Nobody should conclude
"pre-existing" from blame on the flagged file.

THE INTERACTION THAT WAS MISSED: T-1970 landed `frob:quote(...)`
specifically so prose can mention a directive without it being parsed as
one. T-1968 then made unhandled markdown directives loud, but the 105
existing documentation mentions predate the escape and are not wrapped in
it. The two tickets are siblings from one investigation and each is
correct alone; landing the loud half without retrofitting the mentions is
what produced the flood.

DO NOT FIX IT THIS WAY:
- Do NOT revert T-1968 wholesale. Its real deliverable -- correcting
  `_MD_WAIVE_HONORED_RULES` so a genuinely unhandled markdown waiver
  refuses instead of silently doing nothing -- is right and was verified
  to add zero findings at the time it was checked.
- Do NOT bulk-wrap all 105 sites in `frob:quote(...)` mechanically
  without reading them. Some may be REAL directives in markdown that
  nothing reads -- exactly the class T-1968 exists to surface. Wrapping
  those as "mentions" would silently re-hide a live defect, converting a
  loud finding into a lie.
- Do NOT downgrade DSL001 to a warning to clear the floor. That restores
  the silence T-1968 removed.
- Do NOT add a blanket exclusion for `CHANGELOG.md`/`docs/**`. Real
  directives legitimately live in docs (`frob:describes`/`frob:enumerates`
  anchors are load-bearing there).

FIX DIRECTION: triage the 105 into (a) genuine prose mentions -> wrap in
`frob:quote(...)`, and (b) genuine but unread directives -> fix or remove
the directive, which is the finding doing its job. Report the split. If
the mention class dominates, consider whether the emitter should treat an
unhandled verb inside a fenced code block or inline-code span as a
mention by default, since that is where documentation quotes syntax.

ACCEPTANCE: unscoped `frob check --only gates` back to 0 errors, with a
reported (a)/(b) split and per-file counts. First test must FAIL before
the fix: assert a documentation line quoting a directive in an inline-code
span does not raise DSL001, and separately assert a genuinely unhandled
live markdown directive still does.
