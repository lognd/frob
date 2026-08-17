---
id: T-1382
title: 'Decouple frob from the Makefile: make every workflow a first-class cross-platform
  frob subcommand'
state: in-progress
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/app/pyfmt_runner.py
- tests/unit/test_pyfmt_runner.py
- docs/guides/agent-playbook.md
- docs/commands/build.md
- tickets/T-1382/ticket.md
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: remove
  glob: src/frob/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_pyfmt_runner.py
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/**
  reason: narrow to CLI wiring for a new ruff-fix/format subcommand plus doc updates;
    other modules stay out of scope for this pass
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/guides/**
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/build.md
  reason: 'TICK009: docs/guides/** matched 35 files; narrow to the one file this pass
    actually edits'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'T-1382 is an in-progress UMBRELLA epic whose implementation work is done
    entirely by its leaves (T-2240 landed; T-2241/T-2242 blocked). Holding src/frob/_cli_parsers/**
    meant the parent blocked its OWN children at frob ticket start -- T-2241 needs
    _cli_parsers/_misc.py and __init__.py. Documented epic-lease-leak remedy: narrow
    an umbrella epic to its ledger files so it never holds implementation scope it
    does not itself edit.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tickets/T-1382/ticket.md
  reason: 'T-1382 is an in-progress UMBRELLA epic whose implementation work is done
    entirely by its leaves (T-2240 landed; T-2241/T-2242 blocked). Holding src/frob/_cli_parsers/**
    meant the parent blocked its OWN children at frob ticket start -- T-2241 needs
    _cli_parsers/_misc.py and __init__.py. Documented epic-lease-leak remedy: narrow
    an umbrella epic to its ledger files so it never holds implementation scope it
    does not itself edit.'
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: docs/commands/**
  reason: 'Same: T-2242 needs docs/commands/release.md and was blocked by the parent
    epic''s glob. The leaves declare their own doc files; the umbrella does not edit
    them.'
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
acceptance:
- text: GIVEN a repo with no Makefile WHEN every documented frob workflow is run THEN
    each works via a frob subcommand alone
  evidence: []
- text: GIVEN Windows (no make, no POSIX shell) WHEN the coverage workflow runs THEN
    it works without shell quoting, backslash line continuations, or GNU-make syntax
  evidence: []
- text: GIVEN docs and agent guidance WHEN a workflow is described THEN it names the
    frob subcommand, with make targets documented only as thin optional aliases
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User directive 2026-08-01: frob must be cross-project and cross-platform, so it cannot depend on a Makefile.

Current state measured today: the Makefile is 528 lines and 21 call sites across src/frob/ reference it (src/frob/_cli_parsers/_core.py, testing/_collect_cpp.py, vet/_supplychain.py, vet/_capability_registry.py, natives/_build.py, strata/_native_staleness.py, scaffold/_managed.py, scaffold/project.py and others).

The sharpest example is 'make coverage'. Its recipe is ~30 lines of GNU-make-escaped POSIX shell -- COVERAGE_PROCESS_START, a generated coverage rc, an xdist run, a 'node down' grep with a full serial re-run, coverage combine, a T-1363 status guard, then a stamp. None of that runs on Windows, and tests/unit/test_makefile_coverage.py has to slice the recipe text out of the Makefile with a regex and re-run it under bash just to test it -- which is itself evidence the logic is in the wrong place. It should be 'frob coverage', implemented in Python, with the Makefile target reduced to a one-line alias.

Suggested decomposition (leaves to be filed as children):
1. frob coverage -- own the whole recipe in Python, including worker-crash detection and the T-1363 never-promote-partial-data guard.
2. frob build/natives -- replace 'make core' and the native build paths.
3. Audit the 21 Makefile references; each is either a workflow to promote or a scaffold template to re-point.
4. Path/shell portability sweep: no bash -c, no backslash continuations, no assumption of a POSIX shell in any code path.
5. Docs + agent-playbook rewrite so guidance names frob subcommands first; keep make targets as documented optional aliases for muscle memory.

Related: the user's standing preference is still to SUGGEST 'make <target>' where one exists, so this is about removing the DEPENDENCY, not deleting the Makefile.