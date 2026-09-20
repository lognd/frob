## Done report

T-3887 F-017/F-018: `frob coverage --full` spawned a bare `pytest` argv[0]
(`frob.testing._coverage_refresh._pytest_argv`), resolving through the
SPAWNING process's own PATH -- a global pytest shim with no visibility
into the checked project's own `.venv` site-packages. Three separate
consumer repos independently reported the identical symptom: the suite
reads RED (collection errors, the just-installed project package not
importable) while the identical arguments through the project's own
runner exit clean. A verified reproduction of this exact mechanism
already existed on disk (from another agent's T-3931 work, reused per
the coordinator's note rather than rebuilt): a fresh scaffold, real `uv
sync`, bare `pytest --cov=src -q tests/` -> 3 collection errors
(`ModuleNotFoundError: No module named 'demo'`); `uv run pytest` (same
args, same dir) -> clean, 92% coverage.

Fix: `_pytest_argv` now builds its argv via `frob.process._project_tool.
project_tool_argv(root, "pytest", ...)` -- `uv run --project <root>
pytest ...` -- the same T-3887/T-4125 mechanism already used for ty/ruff
spawns. Both call sites (`_run_full_suite`, `_run_incremental_or_
restamp`) now pass `root` through.

MISSING PLUGIN vs MISSING BINARY (the dispatch brief's explicit
distinction, reinforced mid-task by the coordinator): the failure this
must prevent is a missing PLUGIN or missing PROJECT PACKAGE, not merely
"some pytest was found". Verified directly, not assumed: built a real
off-repo scaffold project (own pyproject.toml, own `uv sync`'d venv,
`demo` package asserted NOT importable from frob's own interpreter) and
ran `_pytest_argv`/`_pytest_outcome` against it twice --
  (1) without `pytest-xdist` declared as the project's own dependency:
      a real, loud exit-4 usage error (already-existing
      `_PYTEST_UNMEASURABLE_EXIT_CODES`/`degraded=True` handling --
      UNMEASURED, never silently green), exactly the missing-PLUGIN
      failure mode named in the brief;
  (2) with `pytest-xdist` declared: a genuine clean `exit_code=0`,
      `degraded=False` pass, `demo`'s own real test collected and run
      through ITS OWN environment.
This pair is now a permanent test,
test_pytest_argv_off_repo_project_not_importable_from_frob, doing a
real `uv sync` (not mocked) against a `tmp_path` fixture project.

Distinction preserved, not collapsed (per the coordinator's explicit
caution): a project that does NOT declare pytest-xdist and fails under
`uv run` too is an HONEST absent-dependency error, not something this
fix should paper over -- confirmed by NOT silently falling back to a
serial run or to frob's own env's xdist; the real exit-4 surfaces
exactly as before, now from the right (project's own) environment.

Gates: `frob check --ticket T-4148` clean of any error this diff
introduced. FMT001 (two new frob:tests directive lines over 88 cols)
fixed by hand-wrapping with T-0286 continuation backslashes (frob fmt/
`frob format --directives` declines to auto-wrap a noqa-escaped
directive by design -- `canonicalize_text`'s own T-0985 doctrine
-- so this needed the same manual mid-token wrap the codebase's own
_todo_fmt.py docstring already demonstrates). Remaining gate:ARCH/COV/
DOC/DRIFT/SCOPE errors are all in files this ticket never touched
(src/frob/process/_project_tool.py, src/frob/vet/_bare_toolchain.py,
tickets/T-4144, tickets/T-4155, src/frob/check/_python.py,
src/frob/app/ticket_runner/_land_cmd.py) or are the same shared-doc/
test-fan-out SCOPE002 condition T-4146/T-4147 (this sprint's sibling
tickets) already documented and left unaddressed for the identical
reason: docs/modules/testing.md and docs/modules/gates.md are shared
god-docs carrying every module's own anchors, and widening this
ticket's scope into them or into a dozen unrelated tests/test_ticket_*
files (probable-under-capture SCOPE002 noise from _run/_spawn helper
calls this ticket's own tests happen to share with) would be the scope
overreach the agent playbook warns against.

Filed: T-4162 (F-018's remaining preflight-check half, blocked
on T-3936's lease over tests/test_worktree_guard.py -- see that ticket's
own body for the exact reason this couldn't be folded in here).

All 67 tests in tests/test_coverage.py pass; ruff/ty clean on both
touched files.

### Changed
```
 src/frob/testing/_coverage_refresh.py |  17 ++++-
 tests/test_coverage.py                | 114 ++++++++++++++++++++++++++++++----
 tickets/T-4148/ticket.md              |  39 ++++++++++++
 tickets/T-4162/ticket.md    |  32 ++++++++++
 4 files changed, 188 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_off_repo_project_not_importable_from_frob` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_routes_through_project_env` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 4509 warning(s), 935 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, DOC006@tickets/T-4144/ticket.md, DOC006@tickets/T-4155/ticket.md, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
