## Done report

Fix 1 (frob coverage / consumer repos): `native_coverage_refresh`'s
`cov_target` default changed from the bare literal `"src/frob"` to
`None`, resolved at call time by `_resolve_cov_target(root)`: read
`root`'s own `pyproject.toml` `[project].name`, normalize `-` to `_`,
check `src/<pkg>` then `<pkg>` on disk, falling back to the old literal
only when that cannot be determined. Neither existing caller
(`app/coverage_runner.py`, `testing/_coverage_wait.py`) passes
`cov_target` explicitly, so both now measure the scanned repo's own
package. An explicit `cov_target=` still always wins.

Fix 2 (PORT001 re-scope, MEASURED method stated): T-2405 reused
LEXCHECK001's `DETECTOR_PACKAGE_ROOTS` ("is this a detector") for
PORT001's different question ("can this file embed project identity").
`git grep -c '"src/frob' -- 'src/**/*.py'` (2026-08-29) found 31 files
across 7 top-level packages (gates 17, strata 6, tickets 3, app 2,
testing 1, refactor 1, lang 1); 4 of those 7 are NOT `DETECTOR_PACKAGE_
ROOTS` members (T-2466 measured zero `Violation(` constructors in each).
Unlike `arch/`'s T-2466 exclusion (a bounded, package-scoped AST
property measured at zero), no package can be proven safe here the same
way -- "does this module ever hardcode a project-scoped default" is not
bounded by "does it construct a Violation". New function `frob.gates.
_detector_scope.tracked_repo_python_files` returns the UNFILTERED
`tracked_python_files_for_gate` population (repo-wide, mirroring RENDER001/
WALK001's own already-unscoped convention); `port_selfcheck_gate` now
calls it instead of `tracked_gate_files`/`DETECTOR_PACKAGE_ROOTS`.
LEXCHECK001 is unchanged -- its own question genuinely is "is this a
detector".

Measured against this repo with the widened scope: 629 tracked files
scanned (was 213), 16 PORT001-IDENT hits, ZERO PORT001-PATH hits. Of the
16: 15 are legitimate self-reference (frob invoking its own `python -m
frob` CLI in 9 files, or maintainer-facing diagnostic message text
naming a real file in 5 files, or a scanner's own self-exclusion pattern
in 1 file -- the same class as the already-allowlisted `_pii_structural/
_self_match.py`); 1 (`src/frob/graph/cache.py`'s
`_NON_LANGUAGE_FINGERPRINT_PACKAGES = ("frob", "strata-core")`) is a
genuine candidate, filed as T-3433 rather than fixed here.
`src/frob/repo_meta.py`'s `!= "frob"` self-identification check matches
neither AST shape and scans clean, no allowlist needed.

DISCLOSED GAP (also filed, T-3435, not fixed here): even with
the widened POPULATION, PORT001's two DETECTION SHAPES
(`.startswith(...)` argument; Tuple/List/JoinedStr path segment) do NOT
match a bare string-constant assignment -- the exact shape of
`_DEFAULT_COV_TARGET = "src/frob"`, this ticket's own originating
defect. `testing/_coverage_refresh.py` is now correctly IN PORT001's
scanned population, but that specific line still would not have been
flagged by PORT001 as it exists today. Scope (which files) and detection
shape (which code patterns) are separate axes; this ticket fixed the
first per its own acceptance criteria and discloses the second rather
than silently leaving it unstated.

Also filed (found, not fixed, both now resolved directly since already
in this ticket's scope): a pre-existing test
(`tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency::test_pyproject_declares_concurrency_and_sigterm`)
asserted `sigterm is True`, contradicting T-3420's `sigterm = false` fix
that landed on main before this worktree was created -- fixed directly
(the file was already in scope for the new TestResolveCovTarget tests);
T-3436 (filed then dropped once fixed directly) and
T-3434 (a ty win32 diagnostic on T-3420's own
`tests/system/test_coverage_sigterm.py`: `signal.SIGKILL` does not exist
on Windows -- filed, not fixed, that file is not in this ticket's scope)
record both.

MUST-FIRE: tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_is_now_scanned_t3275
MUST-STAY-QUIET: tests/unit/gates/test_port_selfcheck.py::TestPort001::test_legitimate_self_reference_stays_quiet_t3275
THIRD FIXTURE: tests/test_coverage.py::TestResolveCovTarget::test_non_frob_repo_resolves_its_own_package
(plus test_frob_repo_still_resolves_src_frob for the must-stay-quiet half of fix 1,
and test_tracked_repo_python_files_is_repo_wide_not_detector_scoped for the
_detector_scope.py population itself)

`FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist tests/unit/gates/test_port_selfcheck.py tests/unit/gates/test_detector_scope.py tests/test_coverage.py -v`:
80 passed.
`uv run frob test --base main --fallback warn`: python exit=0, 20 test(s).
`frob check --ticket T-3275`: gate:SCOPE 0 errors (459 pre-existing
docs/modules/gates.md anchor-coverage warnings, unrelated to this diff).
Every other gate family is repo-wide/unscoped per the tool's own
scope-note; ty/ruff-format findings present in that report belong to
other files (T-3411/T-3424 tickets, _new.py) not touched by this ticket.

### Changed
```
 tickets/T-3275/ticket.md           | 79 +++++++++++++++++++++++++++++++++++++-
 tickets/T-3433/ticket.md | 30 +++++++++++++++
 tickets/T-3434/ticket.md | 29 ++++++++++++++
 tickets/T-3435/ticket.md | 30 +++++++++++++++
 tickets/T-3436/ticket.md | 33 ++++++++++++++++
 5 files changed, 200 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_is_now_scanned_t3275` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_legitimate_self_reference_stays_quiet_t3275` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_repo_python_files_is_repo_wide_not_detector_scoped` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestResolveCovTarget::test_non_frob_repo_resolves_its_own_package` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestResolveCovTarget::test_frob_repo_still_resolves_src_frob` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestResolveCovTarget::test_unresolvable_name_falls_back_to_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 14 error(s), 4424 warning(s), 856 waived
- error-findings: COV003@tickets/T-2388, COV003@tickets/T-2405, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3275, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
