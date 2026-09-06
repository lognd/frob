---
id: T-4058
title: 'F-262: the vitest stage reports a failure COUNT with no node ids, so a flake
  cannot be told from a regression'
state: queued
kind: bug
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
- src/frob/check/_native.py
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
Consumer logand.app-v2 F-262, 2026-09-06:

  "a standalone `frob check` reported 6 vitest failures WITH NO FAILING TEST NAMES
   in the output; a direct `npx vitest run` and a second `frob check` both passed
   213/216 (3 skips). Non-reproducible, but the summary line GAVE THE AGENT
   NOTHING TO CHASE. When the vitest stage counts failures it should list the
   node ids (IT HAS THE JSON REPORTER OUTPUT) so a flake can be told from a
   regression."

A COUNT WITHOUT IDENTITIES IS NOT A MEASUREMENT, IT IS A RUMOUR. "210/216" tells
the reader that something failed and denies them every fact needed to act:
which test, whether it is theirs, whether it is the same one that failed last
time. The consumer could not even determine whether they were looking at a flake
or a regression -- which is the single question a failing test count exists to
answer.

THE FIX IS CHEAP AND THE CONSUMER ALREADY IDENTIFIED WHY: the stage HAS the JSON
reporter output. The node ids are in hand at the moment the count is computed and
are simply not surfaced. This is not new instrumentation; it is not discarding
what we already have.

THIS IS THE SECOND REPORT OF ONE SHAPE, and they should be fixed together:
  T-4044 (F-243/F-255)  the prettier stage exits nonzero with NO error-severity
                        diagnostic -- four reports, and they cite T-2521 as
                        having already documented it as a known silent-crash gap.
  this                  the vitest stage reports a failure COUNT with no node ids.
Both are tool stages that reduce a rich tool result to a number and drop the
part a human or agent can act on. Whoever takes either should ask the general
question: WHAT IS THE CONTRACT FOR A TOOL STAGE'S OUTPUT? A stage that reports a
nonzero count or a nonzero exit MUST also report identities or a diagnostic;
otherwise it should report that it could not determine them, which is itself
information.

IT ALSO CONNECTS TO THE FLAKE WORK. T-4055 is enumerating a population of
load-sensitive tests on ubuntu, and its whole method depends on being able to say
WHICH test failed on WHICH run. A stage that reports counts without ids makes
that population uncountable in the vitest half of the suite -- so this fix is a
prerequisite for measuring flakes there, not merely a nicety.

DO NOT fix this by making the stage verbose on success. The ask is that a
FAILURE names its subjects; a passing run should stay quiet.

DETERMINE FIRST: does the vitest stage already parse the JSON reporter output for
some other purpose (the collector does -- `collect_ts_tests` runs
`npx vitest list --json`)? If a parser exists, reuse it rather than writing a
second one -- two independent readers of one format is the desync shape that
produced several defects filed today.

MUST-FIRE FIXTURE: a run with a genuinely failing vitest test names that test's
node id in the stage output.
MUST-STAY-QUIET: a fully passing run does not list node ids.
THIRD FIXTURE: a run where the JSON reporter output is unavailable or unparseable
says SO explicitly, rather than reporting a bare count.

ACCEPTANCE
- Failing vitest node ids surfaced from the JSON output already collected.
- The general contract for tool-stage output stated, and checked against T-4044.
- All three fixtures committed.