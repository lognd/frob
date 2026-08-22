## Done report

Changed:
src/frob/testing/_coverage_refresh.py::pytest_load_initial_conftests (new, pytest11 entry-point hook)
pyproject.toml::[project.entry-points.pytest11] (new)
tests/test_coverage.py::TestNeutralizedAddoptsPytest11Entrypoint.test_p_no_xdist_on_cli_no_longer_needs_a_manual_addopts_override (new)

Root cause: T-2032/T-2086 closed the addopts-reinjection hole only for
`frob coverage`'s own internal worker-crash retry (the explicit argv
`_retry_after_worker_crash` builds itself). The operator-facing surface
this ticket's acceptance criteria target -- a plain `pytest ... -p
no:xdist` typed at a shell -- is a different code path entirely: pytest
merges `pyproject.toml`'s `addopts = "-n auto --dist=loadgroup ..."`
into argv before any of this repo's own Python runs, so nothing inside
`_coverage_refresh.py`'s subprocess-argv construction could ever see it.

Investigated a `tests/conftest.py`-based `pytest_load_initial_conftests`
hookimpl first (widened scope to include it via `frob ticket scope
--add`) -- measured directly that it does NOT work: a conftest file is
only imported as a side effect of pytest's OWN default implementation of
that same hook, so a hookimpl the conftest itself defines cannot be part
of the hook-call's already-fixed execution list. Reverted that approach
(scope --remove'd tests/conftest.py again) once confirmed non-functional.

Real fix: `pytest11` entry-point plugin (`[project.entry-points.pytest11]`
in pyproject.toml, pointing at `frob.testing._coverage_refresh`, which
already carries `_strip_xdist_tokens` from T-2032) -- entry-point plugins
autoload strictly BEFORE `pytest_load_initial_conftests` is called on
`args`, the only ordering that can see and mutate the merged addopts
before argparse errors on it. `pytest.Config`/`pytest.Parser` type hints
stay TYPE_CHECKING-only (module already carries `from __future__ import
annotations`) so this adds no hard runtime `pytest` import outside an
actual pytest process. Required `uv sync` to re-register the new entry
point in the editable install's dist-info before it took effect.

Evidence: tests/test_coverage.py::TestNeutralizedAddoptsPytest11Entrypoint::test_p_no_xdist_on_cli_no_longer_needs_a_manual_addopts_override (bound to acceptance[1])
Full-file run: `uv run pytest tests/test_coverage.py -p no:cacheprovider -q -o addopts=""` -- 48 passed (SUITE-RESULT: exitstatus=0 collected=48 failed=0)
Operator repro re-verified: `uv run pytest tests/unit/test_app_style.py -q -p no:xdist` -- 17 passed, no `unrecognized arguments` error (previously failed on main). Confirmed the plugin does NOT disable xdist's own parallelism when `-p no:xdist` is absent (`uv run pytest tests/unit/test_app_style.py -q` still shows "bringing up nodes...").

Filed: none (no out-of-scope work found)
Gates: uv run frob check --ticket T-2068 (native auto-rebuild triggered once during evidence recording; see session output)

### Changed
```
 tickets/T-2068/ticket.md | 59 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 57 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestNeutralizedAddoptsPytest11Entrypoint::test_p_no_xdist_on_cli_no_longer_needs_a_manual_addopts_override` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/testing/_coverage_refresh.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/testing/_coverage_refresh.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2068/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2068/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2068/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2068/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2068/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2068, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@src/frob/testing/_coverage_refresh.py

### Acceptance amendments
- [11] remove: removed 'coordinator pass to confirm and drop if fully subsumed.' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [10] remove: removed 'than dropping (see T-1968-adjacent caution on unilateral drops) -- worth a' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [9] remove: removed 'This ticket may now be a duplicate of already-landed work; flagging rather' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [8] remove: removed 'in _retry_after_worker_crash via _neutralized_addopts/-o addopts=<stripped>.' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [7] remove: removed 'T-2031/T-draft-4aa27f0c) already fixes this exact addopts-reinjection hole' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [6] remove: removed 'NOTE: T-2086 (landed f843ad7ed5ffb32fac8ab304d42fe2f0a5af55ca, successor to' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [5] remove: removed 'root-cause claim end to end. `-o addopts=""` instead worked (15 passed).' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [4] remove: removed "addopts still injected -n auto/--dist=loadgroup, confirming this ticket's" (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [3] remove: removed "even though `-p no:xdist` was passed explicitly on the CLI -- pyproject.toml's" (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [2] remove: removed 'no:xdist` failed with `error: unrecognized arguments: -n --dist=loadgroup`' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [1] remove: removed 'original static reading: `uv run pytest tests/unit/test_app_style.py -q -p' (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
- [0] remove: removed "Operator-side reproduction (2026-08-10), stronger evidence than this ticket's" (reason: cleanup: previous --criterion-file call split one note into per-line fragments due to no blank-line separators; logan, 2026-08-10)
