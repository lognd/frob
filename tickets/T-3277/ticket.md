---
id: T-3277
title: 'A freshly scaffolded project fails its own make check with 16 errors: docs
  promise green immediately, nothing tests scaffold-then-check'
state: done
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
body_changes:
- mode: append
  reason: 'T-3277 done report: re-measurement, fixes categorized, deliverable test
    green, follow-ups filed'
  actor: logan
  at: '2026-08-28'
  old_length: 5389
  new_length: 13706
evidence:
- tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
- tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
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


### Summary (T-3277)

RE-MEASUREMENT FIRST (per brief): the owner's "16 errors, 5 warnings, 12
UNRESOLVED" was taken against a stale global frob binary. Re-measured
against a global install built from this checkout's HEAD (`uv tool
install --reinstall --from . frob`), which already carried today's
landed dependencies (T-3271/T-3272/T-3273/T-3285):

  FRESH BASELINE (before this ticket's fixes): 12 errors, 4 warnings,
  1 unresolved.

  T-3273 already removed all 12 SCHEMA001 UNRESOLVED findings
  (ARCHSCHEMA/DOCBLOCKSSCHEMA/DUPSCHEMA/GATESSCHEMA/GRAPHSCHEMA/
  NATIVESCHEMA/PROFILESCHEMA/REFSCHEMA/TESTINGSCHEMA/TESTRUNNERSCHEMA/
  TOPSCALARSCHEMA) -- confirmed both by reading each resolver's T-3273
  default-fallback code and by measurement (0 SCHEMA001 findings on a
  fresh scaffold). Only FLAGCOV001 remained UNRESOLVED, and it is a
  pre-existing, unrelated defect (diax F-008, filed separately, see
  below) -- not a T-3273 sibling that regressed.

  T-3271/T-3272 were already reflected in the fresh scaffold's layout
  (lands in demo/, no tickets.md).

  The remaining 12 errors + 4 warnings this ticket fixed = exactly
  REF001(8)+REF002(3)=11, OPAQUE001(1), plus ROOT001(2 warn)/COV001(1
  warn)/TEST003(1 warn) -- the ticket's predicted findings minus the
  dozen T-3273 already killed.

  AFTER THIS TICKET'S FIXES (python-tool): 0 errors, 0 unresolved.
  `frob check` exits 0, "0 errors" in output. Verified via
  tests/system/test_scaffold_dx.py::
  test_python_toolchain_scaffold_passes_check_immediately[python-tool]
  (the pre-existing test T-3262 left red -- this ticket's actual job was
  making it pass, per the brief) and via a manual replay: git init ->
  commit -> uv sync -> ruff/ty/pytest --cov -> frob check
  --stamp-coverage -> commit lockfiles -> frob check -> exit 0.

FINDINGS, CATEGORIZED (as instructed, never blanket-waived):

  OPAQUE001 -- TEMPLATE bug. `getattr(logging, below.upper(), ...)` in
  the shared logging filter reads as a runtime capability probe. Fixed
  with `logging.getLevelNamesMapping().get(...)`, a real dict lookup
  (the reporter's own suggested fix).

  REF001 (8) + REF002 (3) -- TEMPLATE bug. Added `[[refs.entrypoint]]`
  declarations (frob's own idiom, matching this repo's frob.toml) for
  .env.example, .github/workflows/*.yml, Makefile, invariants/.gitkeep,
  scripts/bump_version.py, tests/conftest.py, README.md, src/<pkg>/
  __init__.py, uv.lock -- each genuinely read by something outside the
  project's own tracked-file graph. NOT a fix to REF001/REF002's logic;
  T-3273's opposite direction (default-not-declare) does not apply here,
  these entries are project-specific facts about the template's own
  generated file set, exactly what `[[refs.entrypoint]]` exists for.

  DISCOVERY: python-tool (and pyo3-library/pybind11-library/web-app)
  each carry their OWN frob.toml.j2 that SHADOWS the shared
  shared/python/frob.toml.j2 entirely. Editing only the shared file
  first produced zero effect on a python-tool render -- silent, no
  error. Had to apply the fix to BOTH files. Filed a follow-up
  (scaffold-type parity, T-3335) naming this shadowing trap
  explicitly since the other three per-type overrides plausibly carry
  the same undetected gap.

  ROOT001 on .github/ and invariants/ -- GATE bug, deliberately NOT
  fixed here (forbidden-fix #2: no template waivers). Its own documented
  remedy (`<!-- frob:external-reader dir="..." reason="..." -->`) fires
  DSL001 in the scaffolded project, because the verb is not in DSL001's
  markdown allowlist -- a closed loop a user cannot escape via the
  gate's own suggested path. This is diax F-007 (filed: T-draft-
  672af976, body states the blocking relationship explicitly). Left as
  WARN-only (non-blocking for `frob check`'s exit code / "0 errors").

  PRE001/SCOPE001 on frob-coverage.lock.json -- WORKFLOW/DOCS bug, not a
  lint bug. `make check` writes the coverage lock via `--stamp-coverage`
  then immediately re-checks the same tree in one Makefile target with
  no commit in between; PRE001/SCOPE001 correctly flag that as an
  untracked, unticketed diff (same discipline this repo holds itself
  to). DECISION: the stamp step belongs in `make check` (CI should
  refuse a stale/uncommitted coverage artifact); the actual defect was
  docs/commands/scaffold.md promising "green immediately, no manual
  fixups" for a sequence that structurally cannot be atomic. Corrected
  the docs to state the real (still fully scripted) sequence, matching
  what the DX test does, rather than weakening the gate to make the
  false promise true.

  BONUS bug found + fixed while widening: shared tests/system/
  test_build.py.j2's `test_cli_help()` assumes every Python type has a
  `__main__` entry point -- false for python-library (no CLI). Gated it
  behind `{% if project.type != "python-library" %}` (with the matching
  conditional import) so python-library's render doesn't ship a test
  that can never pass.

DELIVERABLE: tests/system/test_scaffold_dx.py's existing (T-3262-owned,
previously red) test now passes for python-tool. Refactored to
`test_python_toolchain_scaffold_passes_check_immediately`, parametrized
over `_PYTHON_TOOLCHAIN_TYPES` (currently `("python-tool",)`) so
widening is a one-line change per type once verified. NOT widened to:
  - python-library: renders, but has its OWN unrelated break
    (TEST001/TEST005/DOC001-shaped: no unit-test coverage matching its
    own src/demo/logging/* tree) -- filed separately, T-3330.
  - pyo3-library/pybind11-library/cpp-library/cpp-tool/web-app: each
    needs a genuinely different toolchain (cargo/cmake/npm, not
    ruff/ty/pytest) -- not a parametrization of this test. All still
    verified to RENDER without error via the pre-existing
    test_all_registered_types_render_without_error. Follow-up filed:
    T-3335 (scaffold-type parity, names the per-type-override
    shadowing trap explicitly).

OTHER TICKETS FILED (diax report items, not independently re-verified
against gate source in this ticket -- filed per the brief's "file
separately, do not fold in" instruction, each flagged as needing
confirmation):
  T-3331  F-008, FLAGCOV001 can only ever measure frob itself
  T-3332  F-007, ROOT001's own remedy fires DSL001
  T-3334  F-012, frob-suggest/--json UX gaps for consumers
  T-3333  F-009, REF001 on frob's own v2 ticket tree

FORBIDDEN FIXES: not used. No known_keys tables pasted into any
template (T-3273 stays the sole SCHEMA001 owner). No waivers added to
the shipped template anywhere.

Changed:
  src/frob/scaffold/data/shared/python/logging/filter.py.j2 (OPAQUE001)
  src/frob/scaffold/data/shared/python/frob.toml.j2 (REF001/REF002, refs entrypoints)
  src/frob/scaffold/data/types/python-tool/frob.toml.j2 (REF001/REF002, refs entrypoints -- the shadowing file)
  src/frob/scaffold/data/shared/python/tests/system/test_build.py.j2 (python-library CLI-test bug)
  tests/system/test_scaffold_dx.py (widened + made green; the ticket's deliverable)
  docs/commands/scaffold.md (corrected the "green immediately, no manual fixups" promise + doc anchors)

Evidence: tests/system/test_scaffold_dx.py::
  test_python_toolchain_scaffold_passes_check_immediately[python-tool],
  test_all_registered_types_render_without_error
  (both green: `uv run pytest tests/system/test_scaffold_dx.py -q` ->
  2 passed)

Filed: T-3330 (python-library scaffold-check, distinct
  findings), T-3331 (F-008), T-3332 (F-007),
  T-3334 (F-012), T-3333 (F-009), T-3335
  (scaffold-type parity across pyo3/pybind11/web-app/cpp, names the
  per-type frob.toml.j2 shadowing trap)

Gates: `frob check --ticket T-3277` -- 0 errors/0 warnings on every
touched file (confirmed by JSON diagnostic filtering); the repo-wide
gate-summary carries 252 pre-existing errors / 3935 warnings unrelated
to this ticket's scope (unchanged before/after except -1 on my own
docs.md fix). Full unscoped `frob check`/`frob test` on frob's own repo
did NOT complete under this session's host load (12-16 load average,
multiple concurrent series) -- UNMEASURED, not passing; explicitly
flagging per the coordinator's instruction rather than implying green.
Retry before land if the box quiets.
