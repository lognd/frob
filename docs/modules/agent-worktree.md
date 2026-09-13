<!-- frob:waive REF002 reason="a new T-4459 module doc anchored from src/frob/doctor.py's frob:doc directive by design -- a second consumer would not be genuine, same posture as ci_report.md/ghio.md/ci_validity.md's identical single-anchor waivers" -->

# Worktree PYTHONPATH and import-source verification (T-4459)

## The bug this fixes

A worktree test run through the ROOT checkout's own interpreter
(`/home/logan/projects/frob/.venv/bin/python -m pytest ...` invoked with a
worktree as `cwd`) silently imports `frob` from the ROOT `src/`, not the
worktree's own branch: the root venv's editable install points its `.pth`
file at `/home/logan/projects/frob/src`, and an unset `PYTHONPATH` never
overrides that. The test run therefore exercises `main`'s code while
believing it is measuring the branch under test -- a false-green (or
false-red) result with no visible symptom at the point of failure.

The other common shape, `uv run` invoked with the worktree as `cwd`, avoids
the wrong-source problem (it builds a fresh venv against that checkout) but
has its own cost: a stray per-worktree `.venv` gets built from scratch,
which has been observed to stall for 50+ minutes under fleet load.

## PYTHONPATH import source (T-4459)

<a id="pythonpath-import-source-t-4459"></a>

Two surfaces close this gap:

1. **`frob agent env <worktree>`** (`frob.app.agent_runner._run_env`,
   T-0574/T-4459) now exports `PYTHONPATH=<worktree>/src[:<inherited>]`
   alongside its existing `FROB_WORKTREE`/`FROB_AGENT`/
   `PYTEST_XDIST_AUTO_NUM_WORKERS` lines, whenever `<worktree>/src`
   exists. Because this is printed as `export PYTHONPATH=...` and the
   command's whole contract is `eval "$(frob agent env <path>)"`, the
   worktree's own `src/` wins over whatever any other checkout's
   `.pth` would otherwise resolve first -- the exported worktree path is
   placed AHEAD of any previously-inherited `PYTHONPATH` on the same
   line. This is deliberately layered as `_run_env`'s own CLI-level
   addition, not folded into `frob.tickets._worktree_guard.
   agent_env_exports` itself, so that function's own contract (its own
   tests assert an exact export-key set for `FROB_WORKTREE`/`FROB_AGENT`/
   xdist bound) stays unchanged.

2. **`frob doctor`** (`frob.doctor.ImportSourceStatus`/
   `_import_source_status`) reports which `src/` the CURRENTLY-RUNNING
   process's `import frob` actually resolved from, compared against the
   `src/frob/__init__.py` the doctor's OWN `root` argument would imply.
   A mismatch (the worktree has its own `src/frob/__init__.py`, but the
   imported module resolves elsewhere) sets `DoctorReport.import_source.
   mismatched = True`, makes `DoctorReport.healthy` `False`, and adds a
   loud remediation line naming both paths and the fix
   (`PYTHONPATH=<worktree>/src`). A doctor run against a root with no
   `src/frob/__init__.py` of its own (an installed tool, no worktree
   layout) has nothing to mismatch against and always reports
   `mismatched = False`.

## The rule

Any worktree test run or CLI invocation that must exercise the CHECKED-OUT
BRANCH's code (not main's), from any interpreter that was not built fresh
against that worktree, MUST first `eval "$(frob agent env <worktree>)"` (or
otherwise set `PYTHONPATH=<worktree>/src` ahead of anything else) so
`import frob` resolves under the worktree. `frob doctor` is the fast way to
confirm this actually happened before trusting any test result that
followed.
