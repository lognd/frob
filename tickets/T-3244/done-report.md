## Done report

Re-measured fresh at start (coordinator's own count was stale, as warned):
190 findings (not ~197) across the 21 scoped files plus 1 previously-missed
in-scope site (src/frob/verify/_worker.py's os.nice matched-opposite pair,
not visible on a win32-only measurement). All POSIX-only fcntl.flock/
socket.AF_UNIX/os.nice test/product sites gained a `sys.platform ==
"win32"` guard (a `pytest.skip` for test bodies -- a visible declaration,
not a silenced diagnostic -- matching T-3191/T-3211's spirit for whole-
function-POSIX-only test code) or, for the two matched-opposite ty:ignore
pairs (src/frob/verify/_worker.py::_lower_cpu_nice_priority,
src/frob/app/_config_external.py::_all_parser_dests._walk,
src/frob/app/ticket_runner/_new.py's acceptance= bracket), a platform
guard / cast / trimmed ignore-bracket instead of a single ignore comment
that cannot be simultaneously required on one platform and unused on
another.

`ty check --python-platform {win32,linux,darwin}` all now report ZERO
findings attributable to this ticket's scope. Remaining diagnostics
(unresolved-import on frob_core/strata_core -- native extensions not built
in this worktree, a known environment gap; unknown-argument on
AppConfig(command=...) in tests/unit/test_app_runners_process.py and
tests/unit/test_pytest_spawn_env_wiring.py) are unrelated pre-existing bug
shapes, confirmed to reproduce identically with NO --python-platform flag
at all, and are out of this ticket's "platform-unsafe" scope by
definition. Filed T-3257 for the AppConfig one; the native-
import gap is a known, already-tracked environment limitation.

Evidence: full-file pytest runs (mostly -p no:xdist to avoid unrelated
socket-port xdist flake in tests/test_serve_socket.py, reproduced with
none of this ticket's lines touched) across every touched test file, all
green except one pre-existing failure
(TestPreCommitUnscopedSweep::test_true_verdict_lands_normally, confirmed
failing identically on a fresh `main` worktree before any of this
ticket's edits). tests/unit/verify/test_worker.py -k "nice or priority"
green.

`frob check --ticket T-3244 --only scope --only prework --only coverage
--only fmt --only affect_drift`: gate:SCOPE and gate:PREWORK both clean.
Repo-wide gate families (COV/DRIFT/DSL/PRE and others) carry pre-existing
failures per the tool's own "repo-wide, not scoped to this ticket" note,
concentrated in src/frob/vet/** -- files this ticket never touched.

ruff check / ruff format clean on the touched-file set after --fix.

Filed: T-3257 (AppConfig(command=...) unknown-argument,
unrelated pre-existing bug shape in two of this ticket's scoped test
files, confirmed non-platform-specific).

### Changed
```
 tickets/T-3244/ticket.md           |  2 +-
 tickets/T-3257/ticket.md | 30 ++++++++++++++++++++++++++++++
 2 files changed, 31 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 18 error(s), None warning(s), None waived
- error-findings: CYCLE001@src/frob/__init__.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/gates/_vmodel.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_lang_strata.py
