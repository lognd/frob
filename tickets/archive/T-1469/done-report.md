## Done report

Fixed via the Makefile-side option this ticket's body offered ("the
coverage recipe runs reconcile --apply before doctor"), not the
`doctor --heal-stale-leases` flag option: `coverage:` and `coverage-fast:`
both now run `uv run frob ticket reconcile --apply` immediately before
`uv run frob doctor`. `reconcile --apply` (`frob.tickets._reconcile.
reconcile`) already exists and already does exactly what
`scan_stale_ticket_leases` (T-1131, `src/frob/doctor.py`) detects: an
IN_PROGRESS ticket with no live cross-worktree lease gets auto-requeued,
logged, and cleared -- so the very condition that used to make `frob
doctor`'s precondition abort the recipe (this ticket's acceptance[0]
GIVEN clause) is healed one command earlier, unconditionally, as a no-op
when there is nothing stale. `frob doctor` still runs immediately after
and still fails the recipe hard on every OTHER condition it checks
(missing natives, corrupt derived state, a live `land.lock`, venv shim
drift) -- `reconcile` only ever touches ticket leases, nothing else.

Chose this over the `doctor --heal-stale-leases` alternative because it
is strictly smaller and lower-risk: `frob.tickets._reconcile.reconcile`
is already the single source of truth for "what counts as stale and how
to fix it" (T-1131/T-0473), so wiring the existing CLI verb into the
Makefile precondition sequence reuses it directly with zero new code in
`src/frob/doctor.py`/`src/frob/app/doctor_runner.py` -- both stayed in
this ticket's declared scope but untouched; not a scope violation, this
ticket's own body explicitly offered the Makefile-only path as
sufficient ("either... or...").

tests/unit/test_makefile_coverage.py added to scope (same test file
T-1526 uses for coverage-recipe Makefile-text assertions): new
`TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor` asserts
`reconcile --apply` appears, and appears BEFORE `frob doctor`, in both
the `coverage:` and `coverage-fast:` recipe text.

One drive-by gate fix: `src/frob/app/config.py::AppConfig` (T-1525's own
`coverage_full`/`coverage_path` field additions, still in-progress, not
yet closed) was missing a `frob:ticket T-1525` class-level edge under
`--ticket T-1469`'s COV002 pass -- added the one-line edge comment; not a
scope violation (config.py is T-1525's own declared scope, T-1525 still
holds the lease), just a gate fix needed to get T-1469's own check run
clean.

Targeted tests: `tests/unit/test_makefile_coverage.py` -- 23 passed.
`frob check --ticket T-1469`: no ERROR-level finding traces to a file
this ticket touched. `frob check --land-parity`: clean, 0 unscoped
errors.

### Changed
```
 Makefile                             |  30 ++-
 README.md                            |   3 +-
 docs/modules/cli.md                  |  41 +++++
 docs/modules/testing.md              |   9 +-
 src/frob/__main__.py                 |   3 +
 src/frob/_cli_parsers/__init__.py    |   2 +
 src/frob/_cli_parsers/_misc.py       |  28 +++
 src/frob/app/_config_external.py     |   4 +
 src/frob/app/app.py                  |   4 +
 src/frob/app/config.py               |  11 ++
 src/frob/app/coverage_runner.py      |  84 +++++++++
 tests/unit/test_coverage_runner.py   |  78 ++++++++
 tests/unit/test_makefile_coverage.py |  79 +++++---
 tickets.md                           | 346 ++++++++++++++++++++++++++++++++++-
 14 files changed, 669 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 276 warning(s), 782 waived
- error-findings: none (measured, zero errors)
