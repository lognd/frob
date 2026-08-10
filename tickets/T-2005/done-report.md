## Done report

`_run_designated_test` (src/frob/gates/_mutation_evidence.py) built an
`env` dict with `PYTHONPATH` pointed at the parent-ref worktree's own
`src/`, but the two-line-later `run_argv(argv, cwd=worktree,
timeout_s=timeout_s)` call never passed it through -- `run_argv`
(src/frob/gitio.py) had no `env` parameter at all, so the built `env`
local was silently dead, and the spawned pytest subprocess inherited the
CALLING process's own environment unchanged. For a pure-Python source
change, `import frob` (or any package under the parent worktree's own
`src/`) resolved via the editable install's `.pth`, i.e. the CURRENT
(already-fixed) working tree, not the checked-out parent commit's
source -- every `PASSED_AT_PARENT` verdict `frob ticket evidence
--check-repro` / the land/close-time BUG002 gate produced for a
pure-Python fix was a potential false positive.

Fix: added `env: Mapping[str, str] | None = None` to `run_argv` and
threaded it through to `guarded_subprocess_run` (which already forwards
any kwarg, including `env`, to `subprocess.run` -- only the wrapper
lacked the parameter). `_run_designated_test` now passes `env=env`.
`docs/modules/testing.md` updated in the same change: its Public API
block now documents the new parameter, and a stale line asserting
`run_argv` "has no env= parameter by design" (which had itself codified
this bug as intentional) is corrected.

### Already-landed tickets audited for suspect BUG002 designation

Searched every ticket carrying a non-null `designated_repro_test`
(`git grep -l "designated_repro_test:" tickets`, then filtered out
`designated_repro_test: null`): 28 tickets total, of which 10 are
already landed (live in `tickets/archive/`): T-1546, T-1670, T-1749,
T-1838, T-1841, T-1848, T-1853, T-1861, T-1882, T-1907. Every one of
these is potentially suspect -- their PASSED_AT_PARENT/FAILED_AT_PARENT
verdict was computed through the exact codepath this ticket fixes,
for any change whose repro test imports pure-Python `frob` source (not
a native-extension change, which would already fail to collect at the
parent ref regardless of this bug, surfacing as NO_VERDICT rather than a
false PASSED). I did NOT re-verify each of the 10 individually against
this fix (out of this ticket's scope and budget) -- that re-verification
is exactly the shape of work this ticket's fix now makes possible
(re-run `frob ticket evidence <id> --check-repro <node-id> --base-ref
<parent>` for each and confirm the verdict is unchanged), and is filed
as a follow-up rather than silently left undone. The remaining 18
non-archived tickets are still open/in-progress; their designation is
re-checked naturally the next time their own `--check-repro`/land runs
under this fix.

### Changed
```
 src/frob/gates/_mutation_evidence.py  |  2 +-
 src/frob/gitio.py                     | 15 ++++++++++++-
 docs/modules/testing.md               | 10 ++++----
 tests/test_gates_mutation_evidence.py | 41 +++++++++++++++++++++++++++++++++++
 tests/test_gitio.py                   | 26 ++++++++++++++++++++++
```

### Evidence
- `tests/test_gitio.py::TestRunArgv::test_env_override_reaches_the_spawned_process` -- unit-level regression: the exact wiring bug (env silently dropped by run_argv), confirmed to FAIL before the fix (NO env kwarg to pass), PASS after.
- `tests/test_gitio.py::TestRunArgv::test_env_none_inherits_the_calling_process_environment` -- companion case: `env=None` still means "inherit", not "empty".
- `tests/test_gates_mutation_evidence.py::TestBugRepro::test_repro_run_actually_uses_the_parent_refs_own_pythonpath_override` -- end-to-end: a module living ONLY under a real git worktree's `src/` (never on this test process's own sys.path, never added implicitly by `python -m pytest`) is importable by `_run_designated_test`'s repro run ONLY if the PYTHONPATH override genuinely reaches the subprocess. Confirmed FAILING (returned `NO_VERDICT`, exit 4 collection error) against the pre-fix source, PASSING (`PASSED_AT_PARENT`) against the fix -- verified by hand: reverted `src/frob/gitio.py` and `src/frob/gates/_mutation_evidence.py` to `git checkout HEAD --`, re-ran, observed both new tests fail with the exact pre-fix symptom, then restored the fix and re-ran to confirm both pass.

All 11 tests in `TestRunArgv` + `TestBugRepro` pass: `uv run pytest
tests/test_gitio.py::TestRunArgv tests/test_gates_mutation_evidence.py::TestBugRepro -p no:cacheprovider -q` -> `SUITE-RESULT: exitstatus=0 collected=11 failed=0`.
`designated_repro_test` was NOT set via `--designate-repro`: the new
regression test is a brand-new test module with no prior existence at
the parent ref at all, so `--check-repro` against it correctly reports
`NO_VERDICT` (could not collect at parent -- the test did not exist
yet), which is a structurally different, expected case from
confirmatory-only (`PASSED_AT_PARENT`) and produces no BUG002 violation
(matching the existing `test_no_verdict_no_violation` precedent).

Filed: T-2019 -- re-verify the 10 archived tickets' BUG002
designations against this fix (see body for the exact recipe and
denominator).

Gates: `frob check --land-parity` clean after `frob ack
src/frob/gitio.py::run_argv` (DRIFT001 on run_argv's signature change,
reason recorded). The 2 remaining unscoped errors seen
(`F401 tests/test_gates_fmt_directives.py`, `F401
tests/unit/test_tickets_evidence_only_scope.py`) are pre-existing and
untouched by this ticket -- confirmed via `git diff main --stat` on both
paths showing zero diff.

### Changed
```
 tickets/T-2005/ticket.md           | 38 ++++++++++++++++++++++++++++-
 tickets/T-2019/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 87 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gitio.py::TestRunArgv::test_env_override_reaches_the_spawned_process` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestRunArgv::test_env_none_inherits_the_calling_process_environment` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugRepro::test_repro_run_actually_uses_the_parent_refs_own_pythonpath_override` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/bug-002-sweep-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2005
