## Done report

Added frob check --files PATH... (AppConfig.check_files) so ruff/ty and
gate execution can be scoped to a caller-given path set instead of the
whole tree. Threaded through check/_python.py (_run_ruff/_ruff_format_result/
_ty_base_cmd/_run_ty/_run_gates), check/__init__.py (_python_tasks, with
per-stage elapsed-time INFO logging and a _REPO_WIDE_STAGES constant for
arch/cycle/dup/exports, which always run unscoped), and gates/_models.py
(GateConfig.files) + gates/__init__.py (REPO_WIDE_GATES constant for
tickets/milestone/release/cross_ticket_leakage/sys). Rapid land's
synchronous pre-land check spawn (_shared_check_spawn_fn in _verify.py)
now accepts files= and appends --files argv; _land_core_invoke in
_land_cmd.py computes it under rapid only, via a new
_rapid_check_scope_files helper: the diff-touched set (_land_touched_paths)
plus every file containing a direct dependent (frob.graph.affects,
max_depth=1) of a symbol defined in a touched file. Standard profile is
unaffected (files=None keeps every argv byte-for-byte unchanged).

Measured (T-4413 acceptance criterion 3): frob check --only lint on this
repo, under heavy concurrent fleet load, took 8s unscoped vs 2s scoped to
a single touched file via --files -- a real 4x speedup at the exact tool
layer the ticket's own prior investigation named as the dominant ~150s
warm-cache floor. The gates stage itself is NOT yet individually
file-filtered: none of the ~50 registered gate functions currently
accept a path-filter parameter -- GateConfig.files reaches run_gates and
is logged, but no gate consults it yet. A full unscoped frob check
--ticket T-4413 --base dev timed out repeatedly (300s/500s/570s/590s)
under sustained fleet load (peak load average 33, 10-12 concurrent frob
check processes from other agents) -- every partial run showed only
pre-existing WARNING-severity findings, zero new errors. Criterion 3 is
verifiably met for the ruff/ty layer and structurally wired for gates,
not fully closed for gates compute -- filing a follow-up for per-gate
file-filtering.

Verification: tests/unit/test_check_scoped_files.py (19 new tests) plus
the full sibling test_check*/test_app_config*/test_land_cmd*/
test_ticket_runner_gate_findings/test_ticket_runner_land_cmd_flags suites
-- all green, 0 failures. frob check --only lint --files <every touched
.py file> . : 0 errors, 0 warnings (fixed an E501 and a Callable type
mismatch my own edit introduced, plus a SYS110 undeclared-public-symbol
finding on REPO_WIDE_STAGES, privatized to _REPO_WIDE_STAGES).

### Changed
```
 docs/commands/check.md                  |  15 ++
 src/frob/_cli_parsers/_check.py         |  16 ++
 src/frob/app/_config_external.py        |  12 +
 src/frob/app/check_runner.py            |   8 +-
 src/frob/app/config.py                  |   9 +
 src/frob/app/ticket_runner/_land_cmd.py |  71 +++++-
 src/frob/app/ticket_runner/_verify.py   |  24 +-
 src/frob/check/__init__.py              | 110 +++++++--
 src/frob/check/_python.py               |  73 ++++--
 src/frob/gates/__init__.py              |  38 +++
 src/frob/gates/_models.py               |   7 +
 tests/unit/test_check_scoped_files.py   | 404 ++++++++++++++++++++++++++++++++
 tickets/T-4413/ticket.md                |  26 +-
 tickets/T-4504/ticket.md      |  69 ++++++
 14 files changed, 841 insertions(+), 41 deletions(-)
```

### Evidence
- `tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_appends_files_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_rapid_check_scope_files_includes_touched_and_dependents` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestRapidLandFilesWiring::test_shared_check_spawn_fn_no_files_omits_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestPythonTasksScoping::test_no_files_is_unscoped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_scoped_files.py::TestRunRuffFilesArgv::test_ruff_check_uses_files_not_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
