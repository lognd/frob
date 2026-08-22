## Done report

Changed:
  scripts/_require_python.py (new: require_python, _required_version)
  scripts/fleet_status.py (guard call at top, before UTC import)
  scripts/frob-telemetry-hook (guard call at top, before UTC import)
  docs/guides/coordinator-scripts.md (invocation fix + new entries)
  tests/unit/conftest.py::_load_script (new, shared)
  tests/unit/test_require_python.py (new)
  tests/unit/test_coordinator_scripts.py (dedup via shared _load_script)

The documented invocation was bare `python3 scripts/fleet_status.py`;
this project's own requires-python (>=3.11) is not guaranteed to be
what bare python3 resolves to, and the failure was a raw ImportError.
scripts/_require_python.py is a single shared guard module, itself
compatible with ANY python3 (no tomllib -- itself 3.11+ -- no syntax
newer than a conservative floor), so it can detect a too-old interpreter
and say so before the interpreter itself crashes on an incompatible
import. Reads requires-python from pyproject.toml via a minimal regex --
the single source of truth, never hardcoded per script (acceptance [2]).
Called as the FIRST statement in both fleet_status.py and
frob-telemetry-hook, before the datetime.UTC import that was failing.

Did NOT rewrite either script to avoid datetime.UTC (per the ticket's
explicit instruction) -- the project requires >=3.11, and coding to an
older installed interpreter would make every future 3.11 feature a
landmine. Did not touch requires-python itself. Checked verify_lands.py/
check_summary.py/bump_version.py for the same version-sensitive shape --
none found (acceptance [5]).

Evidence: tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message
  FAILED_AT_PARENT confirmed at 75c7d93b0 (repro-only commit); PASSED
  after the fix commit 8cd13ae48.
  Also added: TestRequiredVersion (3 tests), test_supported_interpreter_
  is_a_silent_noop, test_exact_boundary_version_passes,
  test_unknown_requirement_fails_open_never_blocks (both must-still-pass
  controls), TestFleetStatusHappyPathUnaffected (subprocess-level pin).
  Full run: tests/unit/test_require_python.py + tests/unit/
  test_coordinator_scripts.py -- 116 collected, 0 failed. Existing
  tests/test_telemetry_hook_script.py + tests/test_hook_diagnosis_
  nudge.py -- 18 collected, 0 failed (unaffected).
  MUST-STILL-PASS acceptance [3] verified manually: copied main's own
  scripts/fleet_status.py into this repo (so REPO resolution matches)
  and diffed its stdout against the fixed version's stdout under the
  project venv -- byte-identical.

Filed: none

Gates: frob check --ticket T-2236 -- gate:SCOPE/gate:PREWORK clean after
  extending scope to the new module and the two touched test files; no
  gate:AFFECT or gate:FMT findings on this diff; the one DUP001 finding
  (an identical _load-a-script-by-path helper newly duplicated between
  the two test files) was fixed for real by extracting it into
  tests/unit/conftest.py::_load_script, not waived.

### Changed
```
 docs/guides/coordinator-scripts.md     |  50 +++++++++++++--
 scripts/_require_python.py             |  74 ++++++++++++++++++++++
 scripts/fleet_status.py                |   8 +++
 scripts/frob-telemetry-hook            |  10 ++-
 tests/unit/conftest.py                 |  19 ++++++
 tests/unit/test_coordinator_scripts.py |  15 +----
 tests/unit/test_require_python.py      | 110 +++++++++++++++++++++++++++++++++
 tickets/T-2236/ticket.md               |  49 ++++++++++++---
 8 files changed, 307 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/unit/test_require_python.py::TestRequirePython::test_older_interpreter_exits_nonzero_with_actionable_message` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2236/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2236/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2236/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2236/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@scripts/_require_python.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
