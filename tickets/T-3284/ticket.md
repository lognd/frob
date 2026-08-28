---
id: T-3284
title: 'frob-suggest false positives: raw-find-name blocks mtime queries it cannot
  answer, make-target contradicts the global prefer-make instruction'
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
scope:
- .claude/hooks/frob-suggest.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-002 and F-004) and
partially re-measured by the coordinator against the live rule table.

The `.claude/hooks/frob-suggest.py` rule table is materialized into
`~/.claude/hooks/`. EDIT THE REPO SOURCE, then run the sync and confirm
`frob claude sync --check` reports no drift -- editing the materialized copy is
a known way to lose the fix.

--------------------------------------------------------------------
F-002: `raw-find-name` fires on a file-TIMESTAMP query it cannot answer
--------------------------------------------------------------------

MEASURED by executing the live `_RULES` table against candidate commands:

    'find . -newermt "-5 minutes"'                -> []              (quiet)
    'find . -newermt "-5 minutes" -name "*.py"'   -> raw-find-name   (FIRES)
    'find . -name "*.py"'                         -> raw-find-name   (FIRES)

So the rule fires whenever `-name` is present, even when the command's actual
question is "what changed in the last five minutes". The suggested alternative,
`frob explore map`, reports project STRUCTURE and cannot answer an mtime
question at all -- the nudge is not merely noisy, it points at a tool that does
not have the answer.

The reporter hit this while auditing whether a scaffold run had clobbered
existing files -- i.e. while investigating a real bug (F-001, now T-3271).

FIX: add a negative pattern exempting time predicates -- `-newer*` (all its
forms: -newer, -newermt, -newerct, ...), `-mmin`, `-mtime`, `-cmin`, `-ctime`,
`-amin`, `-atime`. This mirrors the negative pattern T-2908 already added to
this same rule for path-scoped finds, and the `-- <path>` exemption on
`recursive-grep`. Do NOT remove the rule; an unscoped `find -name` over .venv/
and twenty worktrees is still worth nudging.

--------------------------------------------------------------------
F-004: `make-target` contradicts a standing global instruction
--------------------------------------------------------------------

MEASURED: the rule has NO negative pattern at all (`None`), so it fires on
every make invocation:

    'make check'   -> make-target
    'make test'    -> make-target
    'make install' -> make-target

Its message says "Workflows belong in frob subcommands, not GNU-make recipes
(cross-platform directive) -- make is not available everywhere this has to
run." That is a real standing directive (T-1382) and must not be discarded.

But it collides with two other true things:
  1. The user's global CLAUDE.md says "Always suggest `make <target>` over the
     raw command."
  2. `frob scaffold` GENERATES a Makefile with exactly these targets, and
     `docs/commands/scaffold.md` documents `make check` as the thing a new user
     runs. The hook blocks the workflow our own scaffold ships.

THIS NEEDS AN OWNER DECISION, NOT A UNILATERAL EDIT. Do not simply delete the
rule or blanket-exempt make. Present the options with your recommendation and
say which you took:
  (a) Exempt the standard scaffold-generated targets (install/format/lint/
      typecheck/test/coverage/check). Narrow, matches the reporter's suggestion,
      keeps the nudge for ad-hoc recipes.
  (b) Fire only where an equivalent `frob` subcommand exists -- this is the
      rule's actual intent ("prefer frob over make" is only meaningful if frob
      can do the job) but needs a mapping the hook does not currently have.
  (c) Scope the rule to the frob repo itself, where T-1382's portability
      directive applies to frob's OWN workflows, and stay quiet in consumer
      repos that legitimately have a Makefile.
(c) is the coordinator's reading of the tension -- T-1382 is about frob not
DEPENDING on make, not about users never running it -- but it is a judgement
call about two of the owner's own instructions, so state your reasoning and
flag it for review rather than treating it as settled.

--------------------------------------------------------------------
Required of both
--------------------------------------------------------------------

MUST-FIRE FIXTURE per rule: the shape each rule exists to catch still fires
(an unscoped `find . -name`, and whatever make invocation survives your F-004
decision).
MUST-STAY-QUIET FIXTURE per rule: the reported false positive is silent.

Test the rules by EXECUTING the real `_RULES` table, not by eyeballing regexes.
T-2031's own near-miss in this same file was caught exactly that way, and the
coordinator's measurements above were produced by loading the table and running
candidate commands through it -- reuse that approach.

DO NOT WEAKEN A RULE TO SILENCE A FALSE POSITIVE. T-2908 narrowed three
misfiring rules in this file rather than removing them, and that is the
precedent. A rule that never fires is worse than no rule, because it reads as
coverage.

ACCEPTANCE
- Both false positives silent, both rules still firing on their real shapes.
- Fixtures execute the live rule table.
- `frob claude sync --check` clean after the change.
- The F-004 decision stated with reasoning and flagged for owner review.
