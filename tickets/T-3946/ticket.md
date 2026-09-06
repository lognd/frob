---
id: T-3946
title: 'F-186: ticket evidence rejects leading --accepts with no hint (F-126 recurrence,
  same consumer twice)'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ticket/_evidence.py
  reason: 'filed scope named _cli_parsers/_ticket/_evidence.py, which does not exist
    -- I invented the path from the verb name for the second time in one session instead
    of grepping. Measured: all three --accepts definitions live in _cli_parsers/_ticket/_closeout.py
    at lines 132, 244 and 410'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'filed scope named _cli_parsers/_ticket/_evidence.py, which does not exist
    -- I invented the path from the verb name for the second time in one session instead
    of grepping. Measured: all three --accepts definitions live in _cli_parsers/_ticket/_closeout.py
    at lines 132, 244 and 410'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-186, 2026-09-06:

  "frob ticket evidence requires --accepts AFTER the node ids; leading placement
   is rejected with no hint. T-0171's agent hit it again. Accept both orders or
   say so in the error."

THIS IS A RECURRENCE OF F-126, which is the whole reason it is worth filing
rather than shrugging at. The same consumer hit the same argument-order trap
twice, with different agents, on different tickets. A friction that recurs is not
a one-off user error; it is a design defect with a measurable repeat rate.

THE DEFECT IS THE SILENT REJECTION, NOT THE ORDERING. argparse rejecting an
interleaved optional among positionals is ordinary Python behaviour. What makes
it cost a cycle every time is that the error does not NAME the cause: the user
sees a rejection and has no way to learn that moving the flag after the ids
fixes it. The consumer's ask is explicitly either-or -- "accept both orders OR
say so in the error" -- and the second half alone would close it.

PREFER ACCEPTING BOTH ORDERS. This repo's standing doctrine is automatic over
commands: a rule the user must REMEMBER has a nonzero failure rate no
documentation drives to zero, and this one has now demonstrated its rate. If
argparse cannot be made to accept the leading form cleanly (a nargs="+"
positional followed by an optional is the classic ambiguity), then the error
message MUST name the fix in prose -- something a reader can act on without
already knowing the answer.

DO NOT close this by documenting the ordering in a guide. The user who hits this
is mid-command, not reading docs, and F-126 proves documentation did not prevent
the second occurrence.

CHECK THE WHOLE CLI SURFACE, NOT JUST THIS VERB. Any other subcommand pairing a
variadic positional with an optional flag has the identical trap. Enumerate them
and report the list -- fixing only the verb that was reported twice leaves the
rest armed.

MUST-FIRE FIXTURE: the leading-placement form either succeeds, or fails with an
error whose text names the ordering as the cause.
MUST-STAY-QUIET: the currently-working trailing form is unchanged.

ACCEPTANCE
- Both orders accepted, or an error that states the fix; say which was chosen
  and why.
- Every other variadic-positional-plus-flag subcommand enumerated, with its
  status stated.
- Both fixtures committed.