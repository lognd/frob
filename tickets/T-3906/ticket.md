---
id: T-3906
title: 'consolidate the format/fmt split: same word, two operations, and only one
  of them has --check'
state: queued
kind: ux
origin: human
created: '2026-09-05'
priority: high
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
OWNER DIRECTIVE 2026-09-05: "Look at the verbs; I particularly don't like the
format/fmt split." Scheduled PRE-ALPHA -- the CLI surface is far cheaper to
change before a release than after.

MEASURED 2026-09-05:

    frob format [-h] [--select-imports-only] [path]
    frob fmt    [-h] [--check] [--json] [--include-test-corpora] [path]

`format` formats PYTHON CODE (ruff, plus import selection). `fmt` wraps FROB
DIRECTIVE COMMENT LINES (the FMT001 family). Those are different operations on
different things, and the two verb names are THE SAME WORD. Nothing in either
name distinguishes them, so the only way to know which is which is to have read
the source.

THERE IS ALSO A FUNCTIONAL ASYMMETRY UNDERNEATH THE NAMING, and it is arguably
the worse half:
  - `fmt` has `--check`; `format` DOES NOT. So the directive formatter can
    check-without-writing and the CODE formatter cannot -- backwards from every
    formatter convention (ruff format --check, black --check), and it means
    `frob format` can only be run destructively. A user who wants "is this
    formatted?" for code has no answer.
  - `fmt` has `--json`; `format` does not.
Whatever is decided about the names, the `--check` gap is a real capability hole
and must close.

PRECEDENT: FROB HAS ALREADY SOLVED THIS SHAPE THREE TIMES. The verb groups
exist for exactly this -- `explore` (T-1238), `quality` (T-1567), `design`
(T-1568), `ops` (T-1569) each consolidated scattered verbs under one name, each
keeping the members usable standalone. This is not a new pattern to invent; it
is the established one, not yet applied here.

RECOMMENDED SHAPE, but make the call yourself and give the reasoning:
    ONE `frob format` verb formatting both, scoped by flag
    (`--code` / `--directives`, default both), with `--check` and `--json`
    applying to the whole thing. `fmt` becomes a deprecated alias through a
    sunset window -- `frob:deprecated` with `sunset=`/`ticket=` already models
    exactly that, so the deprecation is expressible and enforceable rather than
    a note in a changelog.

THE ALTERNATIVE, if they genuinely should stay separate: rename by WHAT THEY
FORMAT rather than by abbreviation length. But answer the question a new user
asks in their first hour -- "why are there two?" -- in the help text itself, or
the split will keep costing that hour.

CHECK BEFORE CHANGING:
  - who calls each verb: CI workflows, the scaffold templates, docs/, the agent
    playbook, .claude/hooks, and any frob-suggest remedy string. A rename that
    misses a remedy string produces the T-3859 defect (a remedy naming a flag
    the verb does not accept).
  - whether `--select-imports-only` has a natural home under the consolidated
    flag set, or is code-specific and should be scoped to `--code`.
  - T-3312 is already filed: `frob fmt` accepts only ONE path argument while
    FMT001's hint implies a list. Fold it in if the surface is being reworked
    anyway; a list-of-paths is the right shape for both halves.

DO NOT break the standalone-usability property the other groups preserve. Those
consolidations kept every member runnable directly; a consolidation here that
forces `frob format --directives` where `frob fmt` used to work is a regression
for every existing script until the sunset passes.

MUST-FIRE FIXTURES:
  - `frob format --check` on an unformatted tree exits non-zero and writes
    nothing
  - the deprecated alias still works and emits its deprecation notice
MUST-STAY-QUIET:
  - a formatted tree passes `--check` cleanly for both halves
  - existing invocations in CI, scaffold templates and the playbook keep
    working through the sunset window

ACCEPTANCE
- The consolidation-vs-rename decision stated with reasoning.
- The `--check` gap closed for code formatting regardless of which is chosen.
- Every caller enumerated and updated, remedy strings included.
- T-3312 folded in or explicitly deferred with a reason.
- Deprecation expressed via frob:deprecated with a real sunset and ticket.
- All fixtures committed.
