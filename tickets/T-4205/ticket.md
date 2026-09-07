---
id: T-4205
title: the reference gate's message describes a broader scan than it performs, so
  a consumer added four citations that could never count
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a file referenced only by bare prose mentions, when the gate runs, then
    the finding is still reported
  evidence: []
- text: given a file referenced by a backtick-wrapped multi-component path, when the
    gate runs, then that reference is credited
  evidence: []
- text: given the refusal message, when it is printed, then it names the accepted
    reference positions and the in-place remedy
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE REFERENCE GATE'S MESSAGE DESCRIBES A BROADER SCAN THAN IT PERFORMS, AND A
CONSUMER PAID FOR THE DIFFERENCE FOUR TIMES. Reported as logand.app-v2 F-390.

They created a decision record and cited it by full path from four tracked files:
a markdown link in their doc index, and PLAIN PROSE mentions in two specification
rows and a done report. Every mention used the exact repo-relative path. The gate
kept reporting "has exactly one inbound reference", crediting only the markdown
link, through every one of those additions.

THE BEHAVIOUR IS CORRECT AND DELIBERATE. Our own module documents it: the
auto-scan counts a path named in a real reference SYNTACTIC position -- a markdown
link, a quoted string literal, a backtick-wrapped multi-component path, a
directive target, or a non-python include -- and NEVER a bare prose or table
mention. The reason is recorded and measured: a naive whole-text substring match
produced an 86% FALSE-POSITIVE RATE, in both directions. That decision should
stand. Do not "fix" this by counting prose.

THE DEFECT IS THAT THE MESSAGE SAYS OTHERWISE. The refusal text tells the reader
it "checked path/basename mentions", which is exactly what the consumer did four
times, each time reasonably expecting it to count. The message describes the
INPUT the scan considers rather than the POSITIONS it accepts, and the gap between
those two is the entire defect.

THE CHEAP REMEDY WAS ALREADY AVAILABLE AND THE MESSAGE DID NOT NAME IT. A
backtick-wrapped multi-component path DOES count. Their prose mentions used the
exact path; had any one of them been wrapped in backticks, the reference would
have been credited and no further work would have been needed. Instead they
concluded the scan was broken and worked around it with a configuration entry.
One sentence in the message would have saved all four attempts.

THIS IS THE SIXTH REFUSAL-MESSAGE DEFECT OF THIS DRIVE. The others reported a
count with no lines, blamed the operator for the tool's own edit, asserted a
ticket state without naming its source, collapsed two causes onto one error name,
and named a remedy verb that does not perform the remedy. The pattern is
consistent: the refusals are CORRECT and their explanations are not, and each one
costs a debugging session.

WHAT TO DO
  1. Make the message state what an accepted reference LOOKS LIKE, not what the
     scan reads. Name the accepted positions, and name the cheapest one -- a
     backtick-wrapped path -- as the fix a doc author can apply in place.
  2. Keep the narrowness. Say in the message that a bare prose mention is
     deliberately not counted, so a reader stops trying rather than repeating the
     attempt with a fourth file.
  3. Name the configuration remedy for the case where prose really is the only
     consumer, since markdown carries no waiver syntax and that is the documented
     escape for this exact situation.

MUST-FIRE FIXTURE:   a file referenced only by bare prose mentions still reports
                     the finding -- the narrowness is preserved.
MUST-STAY-QUIET:     a file referenced by a backtick-wrapped multi-component path
                     is credited, exactly as today.
THIRD FIXTURE:       the refusal message names the accepted reference positions
                     and the in-place remedy.

ACCEPTANCE
- The message describes accepted positions rather than scanned input.
- The backtick-wrapped path remedy named explicitly.
- The deliberate exclusion of bare prose stated in the message.
- No change to what the scan actually accepts.
- All three fixtures committed.
