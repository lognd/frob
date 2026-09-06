---
id: T-4108
title: frob ticket close silently keeps only the last evidence command while accumulating
  every acceptance index, so criteria bind to the wrong evidence and the close succeeds
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: high
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
designated_repro_test: null
acceptance:
- text: given two evidence commands passed to one frob ticket close, when the invocation
    is parsed, then it is refused with a message naming the per-call evidence path
  evidence: []
- text: given one evidence command and several acceptance indexes, when the close
    runs, then that command binds to all of them exactly as before
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket close` SILENTLY DISCARDS ALL BUT THE LAST EVIDENCE COMMAND WHILE
KEEPING EVERY ACCEPTANCE INDEX, so a caller who pairs two commands with two
criteria gets one command bound to both. Reported as logand.app-v2 F-306 against
T-0265: closing with two command/index pairs recorded only the second command,
and all four criteria ended up bound to it.

THE MECHANISM IS AN ARGPARSE ASYMMETRY, four lines apart in
`src/frob/_cli_parsers/_ticket/_closeout.py`:

    line 141-145   the evidence-command flag: NO action, so argparse
                   LAST-WINS. The first value is overwritten and gone.
    line 147-153   the acceptance-index flag: action="append", default [],
                   so every value ACCUMULATES. Its own help text says
                   "(repeatable)".

The node-id evidence flag immediately above (line 139) is also documented
"(repeatable)". So of the three flags in this block, two accumulate and the one
in the middle does not -- and nothing says so. A caller reading the help sees
"repeatable" twice and reasonably infers the pairing works positionally.

WHY THE FAILURE IS WORSE THAN A DROPPED FLAG. If the command had simply been
lost, the close would have failed with an unbound criterion and the caller would
have learned something. Instead the surviving indexes bind to the surviving
command, every criterion looks covered, and the close SUCCEEDS. The ticket's
record now asserts that command B is the evidence for criterion 1, which is
false. This is the silent-zero shape applied to the record rather than to a
measurement: a failed accounting rendered as a clean one, and the wrong data is
durable -- it is what the closed ticket will say forever.

THE FIX IS NOT "MAKE IT APPEND TOO". Adding action="append" makes two flat lists
whose pairing is implied by position, which is exactly the fragile shape that
produced this report -- and it silently changes meaning for any existing caller
passing one command and several indexes (today that correctly binds one command
to many criteria, which is a legitimate use). The consumer's own report offers
the alternative and it is the right one: REJECT THE SECOND PAIR LOUDLY. A close
is a durable record; refusing an ambiguous invocation costs one retry, while
guessing costs a false record nobody re-reads.

So: detect a second evidence-command on this verb and refuse with a message that
names the working alternative -- bind evidence in separate `frob ticket evidence`
calls, each with its own acceptance index, then close. That path already exists
and already works per call; the ticket for it is the discoverability sibling
T-4106.

CHECK THE SIBLING VERBS IN THE SAME FILE. The same flag block is defined at least
twice more (around line 247 and line 368), and line 227's docstring says one of
them deliberately shares close's flags. Determine for EACH whether the
command flag accumulates, and whether the same silent last-wins exists there.
Do not assume the fix at one site covers the others -- and do not assume they
should all behave identically without saying why.

MUST-FIRE FIXTURE:   two evidence commands passed to one close are refused, with
                     a message naming the per-call evidence path.
MUST-STAY-QUIET:     one command with several acceptance indexes still binds that
                     one command to all of them, unchanged -- this is a supported
                     use and must not regress.
THIRD FIXTURE:       the sibling verb(s) sharing this flag block behave as
                     decided above, proven rather than assumed.

ACCEPTANCE
- A second evidence command on a close is refused, not silently dropped.
- The one-command-many-criteria case is byte-for-byte unchanged.
- Every site defining this flag block is enumerated and its behaviour stated.
- No flag is changed to append as a shortcut.
- All three fixtures committed.
