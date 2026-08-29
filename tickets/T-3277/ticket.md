---
id: T-3277
title: 'A freshly scaffolded project fails its own make check with 16 errors: docs
  promise green immediately, nothing tests scaffold-then-check'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
- src/frob/scaffold/data/shared/python/**
- src/frob/scaffold/data/types/python-library/**
- docs/commands/scaffold.md
- src/frob/scaffold/data/types/python-tool/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/data/shared/python/**
  reason: template/doc fixes DV re-measurement showed still needed after T-3273/3271/3272
    landed
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/scaffold/data/types/python-library/**
  reason: template/doc fixes DV re-measurement showed still needed after T-3273/3271/3272
    landed
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/commands/scaffold.md
  reason: template/doc fixes DV re-measurement showed still needed after T-3273/3271/3272
    landed
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/scaffold/data/types/python-tool/**
  reason: python-tool type-specific frob.toml.j2 overrides the shared template DV's
    SCHEMA001 fix lives in -- REF001/REF002 fixes must land here, not just shared/
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL FIRST USE (../diax FROBLEMS.md F-005, frob 0.530.0,
2026-08-28). This is the single most damaging bug for a new user, because it is
the first thing they do and the docs promise the opposite.

`docs/commands/scaffold.md` states: "`frob scaffold new <type> demo && cd demo
&& git init && make check` should go green immediately, with no manual fixups".

ACTUAL, measured by the owner on a fresh python-tool scaffold:
    16 errors, 5 warnings, 12 UNRESOLVED gates.

BREAKDOWN AS REPORTED (re-measure each; do not take these counts on trust):

  12x *SCHEMA001 UNRESOLVED -- the template frob.toml declares none of the
      known_keys tables. ALREADY OWNED by T-3273 (make them default internally
      rather than shipping more boilerplate). Do NOT fix it here by pasting
      the tables into the template; that is the opposite of T-3273's direction.
      Coordinate.

  11x REF001 + 3x REF002 on the scaffold's OWN files -- README.md, Makefile,
      the workflows, scripts/bump_version.py, tests/conftest.py, the package
      __init__.py, uv.lock. The scaffold generates files its own gates then
      flag as unreferenced.

  OPAQUE001 in the template's logging/filter.py (`getattr(logging, name)`).
      The reporter's own fix was `logging.getLevelNamesMapping().get(...)`.

  COV001 on scripts/bump_version.py::PYPROJECT (a public module constant with
      no doc edge) and TEST003 "interface scripts has 0 integration tests" --
      both against the template's own script.

  ROOT001 warns on .github/ and invariants/ -- both directories the scaffold
      itself creates.

  PRE001/SCOPE001 -- `make check`'s own `frob check --stamp-coverage` step
      writes frob-coverage.lock.json, which is then an unticketed diff against
      main. The documented workflow dirties the tree it just checked.

THE PATTERN, and it is the point of this ticket: nearly every finding is frob
flagging FROB'S OWN GENERATED OUTPUT. The scaffold and the gates disagree about
what a correct project looks like, and the scaffold is the one shipping to
users. A new user's first `make check` tells them their brand-new untouched
project is broken in 16 ways.

WHY OUR OWN CI NEVER CAUGHT IT: frob's CI checks the FROB repo, which is not a
scaffolded project. Nothing anywhere runs "scaffold a project, then check it".
That is the structural gap -- same shape as the dogfooding blind spot in
T-3275, where a value correct for frob is wrong everywhere else.

WHAT TO BUILD:
  1. A test that SCAFFOLDS a project into a temp dir, git-inits it, and runs
     the real gate against it, asserting green. That test is the deliverable;
     the individual fixes are what it forces. Without it this regresses the
     next time either side moves.
     Note tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_
     check_immediately already exists and is currently FAILING (owned by
     T-3262). Check whether that test already encodes this and is simply not
     green, in which case this ticket is "make it pass and widen it to every
     type", not "write it". Determine which before building.
  2. Fix each finding on its merits. Some are template bugs (OPAQUE001, the
     missing refs entries); some are gate bugs (ROOT001 flagging directories
     the scaffold creates -- invariants/ is not on ROOT001's allowlist).
     Say which category each one is; do not blanket-waive them in the
     template. A scaffold that ships with waivers for its own gates teaches
     every new user that waivers are how you start a project.
  3. The PRE001/SCOPE001 case is a workflow bug, not a lint bug: the
     documented `make check` dirties the tree. Decide whether the stamp step
     belongs in `make check` at all.

DEPENDENCIES / DO NOT DUPLICATE:
    T-3273  the SCHEMA001 boilerplate (fix by defaulting, not by pasting)
    T-3271  scaffold writes into the wrong directory
    T-3272  ledger v2 default (covers FROBLEMS F-006, the empty tickets.md
            pinning new repos to v1)
    T-3262  the currently-failing scaffold_dx test
These are all live. Read them before starting so you extend rather than fight
them.

STILL UNTICKETED IN THE SAME REPORT, file separately if you confirm them --
do NOT fold them in here:
    F-007  ROOT001's own suggested remedy (`<!-- frob:external-reader -->`)
           fires DSL001, because the verb is not in the markdown allowlist
           while _root_asset_dirs.py reads it with a bare regex.
    F-008  FLAGCOV001 tries to import the CONSUMER's package from inside
           frob's own uv-tool venv, so it can only ever measure frob.
    F-009  REF001 fires on frob's own v2 ticket files (tickets/T-0001/
           ticket.md). Note T-3249 already exempted `tickets.md`; this is the
           v2 tree, adjacent but distinct.
    F-012  frob-suggest points consumers at scripts/check_summary.py, which
           exists only in frob's tree; and `frob check --json` carries no
           top-level exit_code.

ACCEPTANCE
- A scaffold-then-check test exists and passes, for every scaffold type or
  with a stated reason for any excluded.
- Each of the reported findings resolved, categorised as template bug or gate
  bug, with no new waivers in the shipped template.
- The docs' "green immediately" promise is a true statement when you are done,
  or the promise is corrected to match reality. Do not leave them disagreeing.
