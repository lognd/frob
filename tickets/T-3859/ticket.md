---
id: T-3859
title: 'gate remedy strings are never checked against the CLI surface: MILE003 names
  a --set flag the verb does not accept'
state: queued
kind: bug
origin: human
created: '2026-09-05'
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
Reported as typani FROBLEMS T-018.

MILE003's remedy text says:

    set one with `frob ticket milestone T-0015 --set VALUE`

Running exactly that fails: "unrecognized arguments: --set". The verb is
positional -- `frob ticket milestone ID VALUE`.

THE STRUCTURAL POINT, which is worth more than the one-line correction. frob
already checks DOCUMENTATION for command drift: DOC004 has a command-drift tier
that resolves documented invocations against the real CLI surface. Nothing
applies that check to frob's OWN REMEDY STRINGS -- the messages a gate prints
telling a user what to run.

So the repo enforces "the docs must describe real commands" while its error
messages are free to name flags that do not exist. A remedy string is arguably
MORE load-bearing than a doc paragraph: it is read at the exact moment someone
is blocked, by someone who by definition does not already know the answer, and
it is usually pasted verbatim.

This is the same shape as the README drift found today (T-3846): a gate family
checks one population for a property and silently exempts another population
that has the same property. There the exempt population was policy conformance
in README.md; here it is command validity in gate messages.

WHAT TO DO:
  1. Fix MILE003's string to the positional form.
  2. Then the real work: decide whether remedy strings can be checked the way
     documented commands are. Read DOC004's command-drift implementation FIRST
     -- if it resolves a command token against the argparse surface, the same
     resolver may apply to remedy strings with modest plumbing. Report what you
     find before proposing a design.
  3. SWEEP THE EXISTING REMEDY STRINGS regardless of whether a gate lands. Every
     gate message naming a `frob ...` invocation is a candidate. Enumerate them,
     run each, and report the ones that fail. That enumeration has value even if
     the automated check is deferred, and it is the denominator any future rule
     needs.

CAUTION on scope: remedy strings also legitimately name commands that are NOT
frob verbs (git, uv, ruff, cargo). A check that resolves every backticked
command against frob's argparse surface would false-fire on all of those. Say
how they are distinguished -- probably "commands whose first token is `frob`"
-- and make sure the must-stay-quiet fixture covers a remedy naming `git`.

MUST-FIRE FIXTURE:   a remedy string naming a nonexistent frob flag or verb is
                     flagged (use MILE003's own pre-fix text as the fixture).
MUST-STAY-QUIET:     a remedy naming a real frob invocation, and one naming a
                     non-frob command (git/uv/ruff), are both silent.

ACCEPTANCE
- MILE003 corrected.
- DOC004's command-drift mechanism read and reported on for reuse.
- The full remedy-string sweep enumerated, with each failing string named.
- Fixtures committed if a rule lands; if the rule is deferred, say so
  explicitly and file it rather than leaving the sweep as the only outcome.
