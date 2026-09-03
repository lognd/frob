## Done report

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

### Changed
```
 docs/commands/scaffold.md                          |  41 ++++-
 src/frob/scaffold/data/shared/python/frob.toml.j2  |  44 +++++
 .../data/shared/python/logging/filter.py.j2        |   7 +-
 .../shared/python/tests/system/test_build.py.j2    |   4 +
 .../scaffold/data/types/python-tool/frob.toml.j2   |  44 +++++
 tests/system/test_scaffold_dx.py                   |  19 +-
 tickets/T-3277/ticket.md                           | 194 ++++++++++++++++++++-
 tickets/T-3330/ticket.md                 |  60 +++++++
 tickets/T-3331/ticket.md                 |  51 ++++++
 tickets/T-3332/ticket.md                 |  54 ++++++
 tickets/T-3333/ticket.md                 |  29 +++
 tickets/T-3334/ticket.md                 |  48 +++++
 tickets/T-3335/ticket.md                 |  80 +++++++++
 13 files changed, 667 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 83 error(s), 3938 warning(s), 885 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-0089, COV003@tickets/T-0148, COV003@tickets/T-0720, COV003@tickets/T-0742, COV003@tickets/T-0996, COV003@tickets/T-1062, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3287/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
