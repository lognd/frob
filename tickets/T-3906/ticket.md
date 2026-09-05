---
id: T-3906
title: 'consolidate the format/fmt split: same word, two operations, and only one
  of them has --check'
state: in-progress
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
scope:
- src/frob/app/fmt_runner.py
- src/frob/app/pyfmt_runner.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/config.py
- src/frob/app/app.py
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_todo_fmt.py
- src/frob/gates/_waive.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/check/_python.py
- Makefile
- docs/commands/format.md
- docs/commands/fmt.md
- docs/modules/app.md
- docs/modules/cli.md
- docs/index.md
- docs/guides/agent-playbook.md
- docs/guides/agent-playbook-appendix.md
- tests/unit/test_pyfmt_runner.py
- tests/test_gates_fmt_directives.py
- tests/unit/test_fmt_wiring_reachability_t2761.py
- tests/gates_suite/test_waive.py
- tests/unit/test_makefile_coverage.py
- src/frob/app/_config_external.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_app_runners_t0875_leaf_collision.py
- tests/unit/test_format_consolidation_t3906.py
- src/frob/scaffold/data/shared/python/Makefile.j2
- src/frob/scaffold/data/shared/python/README.md.j2
- src/frob/scaffold/data/shared/python/docs/index.md.j2
- tickets/T-3908/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/fmt_runner.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/app.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/gates/_fmt_directives.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/gates/_todo_fmt.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/check/_python.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: Makefile
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/commands/format.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/commands/fmt.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/app.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/cli.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/index.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/agent-playbook-appendix.md
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_pyfmt_runner.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_fmt_wiring_reachability_t2761.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/gates_suite/test_waive.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-3906: consolidate frob format/fmt surface'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-3906: fmt/format CLI args must be wired through from_external''s field
    tuples'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_app_runners_json_guard_t2492.py
  reason: 'T-3906: fmt_path/format_path renamed to fmt_paths/format_paths (T-3312
    list support), these tests construct AppConfig directly with the old field name'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_app_runners_t0875_leaf_collision.py
  reason: 'T-3906: fmt_path/format_path renamed to fmt_paths/format_paths (T-3312
    list support), these tests construct AppConfig directly with the old field name'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_format_consolidation_t3906.py
  reason: 'T-3906: dedicated MUST-FIRE/MUST-STAY-QUIET fixture tests for the format/fmt
    consolidation'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-3906: docs edits + scaffold template comment updates + the T-3908 sunset-followup
    ticket this consolidation files'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/scaffold/data/shared/python/Makefile.j2
  reason: 'T-3906: docs edits + scaffold template comment updates + the T-3908 sunset-followup
    ticket this consolidation files'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/scaffold/data/shared/python/README.md.j2
  reason: 'T-3906: docs edits + scaffold template comment updates + the T-3908 sunset-followup
    ticket this consolidation files'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/scaffold/data/shared/python/docs/index.md.j2
  reason: 'T-3906: docs edits + scaffold template comment updates + the T-3908 sunset-followup
    ticket this consolidation files'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tickets/T-3908/ticket.md
  reason: 'T-3906: docs edits + scaffold template comment updates + the T-3908 sunset-followup
    ticket this consolidation files'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/modules/gates.md
  reason: 'T-3906: revert -- gates.md is a scope-closure hub file (T-3902''s known
    SCOPE002 explosion), unaddable to any ticket scope; reverted the edit instead
    of fighting T-3902'
  actor: logan
  at: '2026-09-05'
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
    ("--code" / "--directives", default both), with "--check" and "--json"
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
    flag set, or is code-specific and should be scoped to "--code".
  - T-3312 is already filed: `frob fmt` accepts only ONE path argument while
    FMT001's hint implies a list. Fold it in if the surface is being reworked
    anyway; a list-of-paths is the right shape for both halves.

DO NOT break the standalone-usability property the other groups preserve. Those
consolidations kept every member runnable directly; a consolidation here that
forces "frob format --directives" where `frob fmt` used to work is a regression
for every existing script until the sunset passes.

MUST-FIRE FIXTURES:
  - "frob format --check" on an unformatted tree exits non-zero and writes
    nothing
  - the deprecated alias still works and emits its deprecation notice
MUST-STAY-QUIET:
  - a formatted tree passes "--check" cleanly for both halves
  - existing invocations in CI, scaffold templates and the playbook keep
    working through the sunset window

ACCEPTANCE
- The consolidation-vs-rename decision stated with reasoning.
- The "--check" gap closed for code formatting regardless of which is chosen.
- Every caller enumerated and updated, remedy strings included.
- T-3312 folded in or explicitly deferred with a reason.
- Deprecation expressed via frob:deprecated with a real sunset and ticket.
- All fixtures committed.
