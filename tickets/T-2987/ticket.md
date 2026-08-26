---
id: T-2987
title: 'Comment bloat: 39.8% of src is prose; frob:waive directives reach 20 lines
  of essay that belongs in the ticket'
state: queued
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Measured 2026-08-26 with `cloc . --vcs=git` plus AST/directive analysis over
`git ls-files "src/**/*.py"`.

WHOLE REPO (cloc): Python 292,895 code / 186,823 comment / 61,839 blank across
1,244 files. A 0.64 comment-to-code ratio, roughly 3x a typical codebase.

SRC ONLY (279,248 lines total):

| category                                   | lines   | % of src |
|--------------------------------------------|---------|----------|
| docstrings (8,044 of them, avg 9.1 lines)  | 73,475  | 26.3%    |
| `#` comment lines                          | 37,560  | 13.5%    |
| -- of which `frob:` directives             | 18,074  |  6.5%    |
| TOTAL PROSE                                | 111,035 | 39.8%    |

DIRECTIVE BREAKDOWN (12,913 directives -> 18,074 lines):

    ticket 4945 | tests 3568 | doc 2603 | waive 1061 | enforces 579
    invariant 135 | raises 12 | todo 4
    1,818 are multi-line; 460 are >= 5 lines

FINDING 1 -- the bindings are NOT the problem. `frob:ticket`, `frob:tests` and
`frob:doc` are 11,116 of 12,913 directives (86%) and are almost all single
lines. A one-line binding buys real traceability at minimal cost. Leave them
alone.

FINDING 2 -- `frob:waive` is the bloat. It is only 8% of directives but
dominates the long tail: all five longest directives in the repo are waivers,
at 18-20 lines each, the longest in `src/frob/tickets/_leases.py`. Waivers
account for the bulk of the 5,161 backslash-continued comment lines.

A waiver reason IS load-bearing -- it justifies suppressing a gate, and this
repo has rightly refused bare waivers. The defect is not that reasons exist,
it is that a 20-line justification lives in a source file. The ticket is the
right home for an argument; the directive should carry a one-line summary plus
the ticket id, preserving point-of-use legibility without embedding an essay.

PROPOSAL for finding 2: cap directive prose (2 lines is a reasonable starting
point) and require anything longer to live in the referenced ticket. Enforce
with a rule, since an unenforced convention will not hold -- this repo's own
doctrine is that warnings rot and only gates stick. The rule must accept a
one-line summary plus a ticket pointer as the compliant form, so the fix
direction is "move the prose", never "delete the justification".

FINDING 3 -- docstrings are the larger mass and may be the real question.
73,475 lines across 8,044 docstrings averages 9.1 lines each, against the
project's own stated standard: "Every public symbol gets a one-line docstring
(WHY/WHAT, never restating the name)." That is 9x the stated rule and 4x the
volume of every directive combined.

This one needs a HUMAN DECISION before any mechanical action, and this ticket
must not pre-empt it. Long docstrings here are frequently doing real work --
recording why a design decision was made, what a prior attempt got wrong, which
ticket superseded which policy. That is institutional memory, and this drive has
repeatedly benefited from it (several agents avoided repeating a landed mistake
purely because a docstring recorded it). Deleting it to hit a line target would
be actively harmful.

So the question to settle is which of these is true:
  (a) the one-line rule still means what it says, and 9.1 lines is drift to be
      corrected; or
  (b) the rule is obsolete in practice and should be rewritten to say what the
      project actually wants (short summary line, followed by rationale where
      rationale genuinely earns its place).
Do NOT mass-shorten docstrings under this ticket. Bring the measurement, get the
decision, then scope the work.

ACCEPTANCE
- A directive-prose cap is enforced by a rule, with a must-fire fixture (an
  over-long waiver) and a must-stay-quiet fixture (a compliant one-line summary
  plus ticket pointer).
- The existing over-cap waivers are migrated: prose moved into the referenced
  ticket, directive reduced to summary plus pointer. Report before/after
  directive-line totals, measured, and confirm no justification was DELETED --
  only relocated.
- Finding 3 is reported to the human with the measurement and an explicit
  recommendation, and is NOT acted on mechanically within this ticket.
