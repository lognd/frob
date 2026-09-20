## Done report

Fixed src/frob/scaffold/data/shared/python/pyproject.toml.j2's
[tool.pytest.ini_options] pythonpath from ["."] to ["src", "."]. MEASURED
on the winrun win32 mirror (frob.exe added to restricted PATH manually,
see below): the real pytest --collect-only traceback behind CI's
truncated COV003 repr was ModuleNotFoundError: No module named 'demo'
inside a spawned xdist worker (popen-gwN) of a freshly scaffolded
python-tool project, even though its `uv sync` editable install had just
reported success. The forkserver PR_SET_PDEATHSIG warnings in the CI
repr are a known-benign win32 red herring (T-2944), not the cause.
Root cause: pythonpath=["."] only ever worked because the src-layout
editable install made `demo` importable; on win32 a `multiprocessing.
spawn`-based xdist worker re-imports site config from scratch rather
than inheriting the parent's already-patched sys.path, so the editable
shim did not reliably survive into the worker. Adding "src" to
pythonpath makes pytest itself put the source directory on sys.path for
every worker -- a no-op on POSIX (verified: still passes there), not
dependent on the editable-install shim surviving a spawned worker.

Verified fail-before/pass-after TWICE: once manually on the winrun
mirror (same failure reproduced with the pre-fix template, gone after
touching the mirror's synced copy of the fix), and once via `frob ticket
evidence T-4406 --check-repro`, which independently confirmed
FAILED_AT_PARENT for the bound node id on this Linux checkout too (a
genuine, not merely Windows-only, repro at the pre-fix commit).

Scope note: T-4406's original scope (src/frob/scaffold/*.py) did not
cover the .j2 template where the actual fix lives; extended via
`frob ticket scope T-4406 --add 'src/frob/scaffold/data/**/*.j2'`
(recorded on this worktree's branch; needs mirroring to main once the
shared root is quiet -- a land was in progress when I tried from
/home/logan/projects/frob).

frob check --ticket T-4406 shows zero NEW errors from this change (the
scope-note in its own output says --ticket scoping covers only gate:
SCOPE/PREWORK plus the diff-driven checks; every remaining error/warning
in the run -- DOC011 stale citation, LARGE001 in
src/frob/testing/_collect.py (another agent's declared COV003/collection
attribution area, explicitly out of my scope per the coordinator's
brief), TICK004/006/010 ledger hygiene -- is repo-wide, pre-existing,
and unrelated to this ticket's one-file template change). ruff-format
reported "1 file would be reformatted" repo-wide; not this ticket's .j2
file (ruff-format only examines .py files) and pre-existing.

### Changed
```
 src/frob/scaffold/data/shared/python/pyproject.toml.j2 | 17 ++++++++++++++++-
 tickets/T-4406/ticket.md                               | 18 ++++++++++++++++++
 2 files changed, 34 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 6 error(s), 4813 warning(s), 959 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/testing/_collect.py, TICK004@tickets.md, TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4417.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4424.json
