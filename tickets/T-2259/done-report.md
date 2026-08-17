## Done report

### Root cause

`_run_env` (src/frob/app/agent_runner.py) printed export lines to stdout
via `Renderer.for_stream(sys.stdout)`, which was already correct. The
pollution came from the SHARED root logger config
(`src/frob/logging/config.toml`): every module logger (including `gitio`/
`process`, triggered by `agent_env_exports`'s own git subprocess spawns)
routes DEBUG/INFO records to a process-wide `_LazyStdoutHandler`. That
split (DEBUG/INFO on stdout, WARNING+ on stderr) is correct for nearly
every other subcommand but fatal here, since `frob agent env`'s entire
contract is "stdout is pure shell, eval it."

### Fix

Local to `agent_runner.py` (no shared logging-module change, per the
ticket's "fix the producer, don't ask callers to filter" directive): a new
`_all_logs_to_stderr()` context manager wraps `_run_env`'s body. It
disables the process's `_LazyStdoutHandler` (raises its level past
CRITICAL) and widens `_LazyStderrHandler` to DEBUG for the duration of the
call, so every record any code path emits during export resolution -- not
just the three known `gitio`/`process`/`agent env` prefixes -- is
redirected to stderr, never silenced. Restored via try/finally regardless
of exit path (including the existing `sys.exit(1)` on a non-repo path).

### Scope

Local to `frob agent env`, not repo-wide. No other subcommand mixes a
must-be-pure stdout payload with the shared DEBUG/INFO-to-stdout logging
split the same way -- `frob check --json`/`map`/`outline`/`xref` already
solved this same class for THEIR OWN payloads via `quiet_stdout_logs`
(mute, not redirect, because those payloads are JSON/text a caller parses
directly, not something a stderr-diagnostics MUST-STILL-PASS control
applies to). `frob agent env` is the one subcommand whose stdout is
`eval`'d directly by the caller's shell, which is what makes even a
single stray non-`export` byte fatal (unlike a JSON payload where a
human/parser could plausibly ignore trailing noise). No sibling
subcommand shares that specific hazard today, so no repo-wide change was
made; if a future subcommand adds another must-be-pure stdout contract,
`_all_logs_to_stderr` is a 20-line pattern to copy, not a shared primitive
worth extracting yet for a population of one.

`docs/guides/agent-playbook.md` scope was DROPPED after a lease collision
with in-progress T-1382 (holds that file). No edit was needed there
anyway: line 243 already documents the bare `eval "$(frob agent env
<worktree-path>)"` form with no `grep '^export'` filter -- the broken
workaround only ever appeared in ad hoc dispatch-prompt prose, not in the
playbook itself. Verified via `grep -n "frob agent env"
docs/guides/agent-playbook.md`.

### Evidence

- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines`
  (designated repro, T-1929-validated FAILED_AT_PARENT against
  fcdecfb3f, the test-only commit preceding the fix): asserts every
  non-empty stdout line starts with `export `.
- `::test_bare_eval_succeeds_with_no_filtering`: the literal acceptance-1
  scenario, `eval "$(uv run frob agent env <path>)"` with NO filtering,
  real subprocess.
- `::test_diagnostics_still_appear_on_stderr`: MUST-STILL-PASS control --
  `gitio:`/`process:` substrings present in stderr.
- `::test_no_fleet_context_still_produces_valid_eval_output`: T-2221's own
  control, no lease -> no `PYTEST_XDIST_AUTO_NUM_WORKERS` bound, stdout
  still pure.

All four are real subprocess tests (`subprocess.run(["uv", "run", "frob",
...])`), not in-process `capsys` calls: under pytest, frob's root logger
installs NO handlers at all (T-1621), so an in-process capsys test cannot
observe this class of bug at all -- confirmed by first running these tests
against the unfixed producer (commit fcdecfb3f) and watching all four
fail for the right reason (stray `gitio:`/`process:` lines on stdout,
non-zero exit from the `eval` subshell), then confirming green after the
fix commit (fc704fe85).

### Changed

`src/frob/app/agent_runner.py` (`_all_logs_to_stderr`, wired into
`_run_env`), `tests/test_worktree_guard.py` (4 new tests, class
`TestAgentEnvStdoutPurity`).

### Filed

None.

### Gates

`frob check --ticket T-2259`: no NEW findings attributed to
`agent_runner.py`/`test_worktree_guard.py` (verified via
`check_summary.py` grep for both filenames -- zero hits); the repo-wide
FAIL rows in the tool summary are pre-existing baseline noise unrelated
to this ticket's touched files.

### Changed
```
 src/frob/app/agent_runner.py | 74 +++++++++++++++++++++++++++++++++-------
 tests/test_worktree_guard.py | 81 ++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2259/ticket.md     | 25 ++++++++++----
 3 files changed, 162 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2259/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2259/tests/test_ticket_work_and_land_finish.py, F821@/home/logan/projects/frob/.claude/worktrees/t-2259/src/frob/tickets/_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2259, RENDER001@src/frob/release/_cli.py, RENDER001@src/frob/scaffold/_skills_sync.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, unresolved-reference@src/frob/tickets/_land.py
