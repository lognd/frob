---
id: T-3229
title: 'frob-suggest promises a verbatim re-run will be allowed; it blocks again as
  repeat #4'
state: queued
kind: bug
origin: human
created: '2026-08-28'
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
CONFIRMED by two independent observers 2026-08-28.

`.claude/hooks/frob-suggest.py` blocks a command and prints, verbatim:

    If you are SURE the raw command is right, re-run it EXACTLY as written and it
    will be allowed; this hook blocks only the first attempt at a given command.

That promise is FALSE. Re-running the identical command blocks again, escalating
to:

    BLOCKED (repeat #4) by frob-suggest [raw-linters] -- this exact shape has now
    recurred several times in this session.

FIRST OBSERVATION (coordinator, this session): running
    uv run ty check --help 2>&1 | grep -iE "platform|python-version" | head -10
was blocked, re-run EXACTLY as the message invited, and blocked again as
"repeat #4".

SECOND OBSERVATION (Series DD, independently, same session): reproduced twice
more with different commands -- `git grep` and `make core` -- both hitting
`BLOCKED (repeat #4)` on the literal re-run.

So this is not specific to one rule or one command shape.

WHY THIS MATTERS MORE THAN THE INCONVENIENCE. The message is the hook's own
documented escape hatch. When following it verbatim does not work, the caller's
only remaining options are to reword the command -- which the hook itself
explicitly forbids ("Do not paraphrase to get around the block -- a reworded
command is a new command and blocks again") -- or to find the `FROB_SUGGEST_ACK=1`
prefix. An escape hatch that does not open, guarding a rule that is otherwise
correct, is how a guard trains people to bypass it. This repo already carries
2,192 `frob:waive` directives against 93 `frob:debt`; teaching agents to reach
for an ack is the same failure at the hook layer.

DO NOT FIX THIS BY WEAKENING THE RULE. `raw-linters` is correct in intent -- a
single linter passing is not the repo being clean, and three of frob-suggest's
rules were found MISFIRING earlier (T-2908) and had to be NARROWED, not removed.
The defect is the gap between what the message promises and what the hook does.

TWO LEGITIMATE FIXES; PICK ONE AND JUSTIFY IT:
  (1) Make the behaviour match the message: genuinely allow the identical
      command on its second attempt.
  (2) Make the message match the behaviour: stop promising the re-run works, and
      state the actual escape (the `FROB_SUGGEST_ACK=1` prefix) on the FIRST
      block rather than only after repeats.
Option (2) is likely safer -- allow-on-repeat can be defeated by a loop -- but
say which you chose and why.

RELATED, NOT CONFIRMED, DO NOT ASSUME: the coordinator also observed that the
`FROB_SUGGEST_ACK=1` example the hook prints placed the prefix before a `cd` in a
compound command, which did not work; the ack had to sit immediately before the
`uv run` segment. Series DD did NOT independently re-verify this and explicitly
declined to claim it. Verify it yourself before fixing it, and if it does not
reproduce, say so.

REMEMBER THE MATERIALIZATION STEP: hooks are materialized from `.claude/hooks/`
into `~/.claude/`. Edit the SOURCE, run the sync, and confirm
`uv run frob claude sync --check` reports no drift. Editing the materialized copy
is a known way to lose a fix -- drift was found and reconciled in this repo
earlier tonight.

ACCEPTANCE
- The promise in the message and the hook's actual behaviour agree. State which
  of the two fixes you took.
- A must-fire fixture: the rule still blocks the shape it is meant to catch.
- A must-stay-quiet fixture: the documented escape, whichever it now is, actually
  works on the first try that uses it.
- `frob claude sync --check` clean after the change.
