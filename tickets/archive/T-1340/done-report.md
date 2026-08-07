## Done report

Built the SuppressionDialect registry and SUPPRESS001, the evidence-driven
suppression-dialect mismatch detector (T-1339 Phase 1).

frob.gates._suppress (new module):
- SuppressionDialect (pydantic model, model_config={}): name, comment
  pattern (regex naming an optional `code` group), and `available` --
  shutil.which-based, a capability limit (oracle exists in THIS process),
  never "configured in this project", per T-1339's DESIGN AMENDMENT.
- suppression_dialects(): registers ty, mypy, ruff/noqa entries.
- _ty_diagnostics/_mypy_diagnostics: real oracle invocations (ty reuses
  frob.check._python._run_ty; mypy is a NEW dev dependency, run directly
  with --check-untyped-defs so it does not go blind on unannotated
  fixtures, and deliberately WITHOUT --warn-unused-ignores per T-1339's
  watch item). mypy never gates frob check -- only this gate's own
  correlation of its diagnostics reads them.
- suppress001_gate/_suppress001_correlate: for every diagnostic a
  reporting dialect emits at file:line, fires SUPPRESS001 iff that line
  is not already suppressed for the reporting dialect's own code AND
  carries a DIFFERENT dialect's suppression comment. No static
  mypy<->ty code mapping table -- each diagnostic supplies its own code.
  Symmetric by construction: whichever oracles are available each get a
  turn as "reporting", so mypy->ty and ty->mypy both fall out of the same
  loop.

Registered "suppress" in frob.gates._ALL_GATES/_CANONICAL_GATE_ORDER and
wired into the thread-pool job dict (I/O-bound, same shape as "fuzz").
Added mypy>=1.10 to [dependency-groups].dev in pyproject.toml (uv.lock
regenerated at land time -- T-0731's land-owned-file guard refuses a
worktree commit to uv.lock, so it is left for `frob ticket land`'s
existing `_sync_uv_lock_for_land` step, which already re-runs `uv lock`
after a version bump; this ticket's dev-dependency addition rides the
same mechanism).

Reworded acceptance [2] as instructed: appended acceptance criterion [3]
stating a dialect with no available oracle (capability limit) produces no
findings for that direction, rather than "not configured in this project".

Verified with the REAL ty/mypy binaries against on-disk tmp_path fixtures
(no mocked tool output) -- both directions (mypy-suppressed/ty-unsuppressed
and the symmetric ty-suppressed/mypy-unsuppressed) fire correctly, the
both-dialects-present and no-suppression-at-all cases report nothing, and
the no-available-oracle case (monkeypatched registry) reports nothing.

Residue (filed as T-1357): SUPPRESS001, once wired into frob check, immediately found a
REAL pre-existing mismatch on main outside this ticket's scope --
src/frob/gates/_debt_deprecated.py:663 carries only a mypy
type:ignore[attr-defined] while ty reports an unsuppressed
unresolved-attribute there. Filed rather than hand-patched:
T-1357 (scope src/frob/gates/_debt_deprecated.py).

Detection only, as scoped -- the Tier-A auto-fix that writes the paired
suppression is the sibling ticket T-1341, untouched here.

### Changed
```
 design/frob.strata           |   9 ++
 docs/modules/gates.md        |  64 ++++++++
 pyproject.toml               |   6 +
 src/frob/gates/__init__.py   |  18 +++
 src/frob/gates/_suppress.py  | 376 +++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates_suppress.py | 226 ++++++++++++++++++++++++++
 tickets.md                   | 127 +++++++++++++--
 7 files changed, 817 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppressionDialects::test_registers_ty_mypy_ruff` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestLineSuppressions::test_bare_ty_ignore_covers_everything` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestLineSuppressions::test_coded_mypy_ignore_extracts_code_set` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestLineSuppressions::test_both_dialects_on_one_line` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestLineSuppressions::test_no_suppression_present` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestRelativize::test_absolute_path_under_root` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestRelativize::test_already_relative_path_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestRelativize::test_path_outside_root_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestRelativize::test_none_file_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_both_dialects_present_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_no_suppression_no_finding` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_no_available_oracle_reports_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 4 error(s), 857 warning(s), 690 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, SUPPRESS001@src/frob/gates/_debt_deprecated.py, TICK003@tickets.md
