---
id: T-2259
title: frob agent env writes gitio/process diagnostics to STDOUT, so the documented
  eval fails with a bash syntax error -- T-2221's xdist bound has been inert fleet-wide
  since it landed
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/agent_runner.py
- tests/test_worktree_guard.py
- src/frob/tickets/_worktree_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/guides/agent-playbook.md
  reason: T-1382 holds an active lease on this file; fix is producer-side in src/frob/app/agent_runner.py,
    doc note can follow in a separate pass
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/app.md
  reason: 'closure: doc anchor + test file for agent_runner.py::run'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_worktree_guard.py
  reason: 'closure: doc anchor + test file for agent_runner.py::run'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/modules/app.md
  reason: app.md is a broad shared module doc covering ~90 unrelated symbols; closure
    would explode scope far beyond this bugfix. Not adding a new public symbol, so
    no new doc obligation is created
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'closure: agent env export logic lives here per test bindings'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output
designated_repro_test: tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines
acceptance:
- text: 'eval "$(uv run frob agent env <worktree>)" succeeds with NO filtering and
    sets the three vars (fails today: bash syntax error)'
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output
- text: stdout contains ONLY export lines -- assert on every line, not just that exports
    are present
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines
- text: 'MUST-STILL-PASS: the gitio/process diagnostics still appear, on stderr, unchanged
    -- redirected not removed'
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr
- text: No-fleet-context case still emits no bound and still produces valid eval-able
    output
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output
- text: agent-playbook.md:243 documents the form that actually works
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 20a25832cc5c7c6dc63278f291a392fddcd924fc
---
# `frob agent env` writes diagnostics to STDOUT alongside the export block, so the documented `eval "$(...)"` fails with a shell syntax error

## Measured evidence (2026-08-16)

The command the playbook prescribes (`docs/guides/agent-playbook.md:243`) does
not work:

    $ eval "$(uv run frob agent env .claude/worktrees/t-2231)"
    /bin/bash: eval: line 1: syntax error near unexpected token `('

Because stdout carries log lines, not just shell:

    gitio: spawning ('git', '-C', '.claude/worktrees/t-2231', 'rev-parse', '--show-toplevel') ...
    process: spawning ['git', '-C', ...]
    gitio: repo_root(...) = /home/logan/projects/frob/.claude/worktrees/t-2231
    agent env: resolved ... -> FROB_WORKTREE=...
    export FROB_WORKTREE=/home/logan/projects/frob/.claude/worktrees/t-2231
    export FROB_AGENT=1
    export PYTEST_XDIST_AUTO_NUM_WORKERS=1

The `(` in `('git', '-C', ...)` is what the shell chokes on. The working form
has to filter:

    eval "$(uv run frob agent env <path> 2>/dev/null | grep '^export')"

Independently hit and reported by an implementer agent working T-2250, then
reproduced directly.

## Why this matters beyond ergonomics

`frob agent env` exists to be `eval`'d -- emitting shell is its entire purpose.
A command whose output is shell code must keep stdout clean; diagnostics belong
on stderr.

The consequence is not cosmetic. T-2221 landed a fleet-aware
`PYTEST_XDIST_AUTO_NUM_WORKERS` bound and it has been **inert across the whole
fleet since it landed**, because the only documented way to apply it fails.
Measured today with six agents live: one worktree carried ~39 processes (the
`pytest -n auto` signature, all 12 cores) while the machine sat at

    Mem:   23 total, 16 used, 1 free, 4 buff/cache, 6 available
    Swap:  24 total,  6 used

1GB free RAM. This repo has previously lost a session to the OOM killer under
this condition. Every agent that "failed to apply the bound" was in fact
running a documented command that cannot succeed.

## Do NOT fix it this way

- **Do NOT tell callers to pipe through `grep '^export'`.** That makes every
  caller responsible for cleaning the channel, and a caller who forgets gets a
  syntax error instead of a missing variable -- which is how this stayed
  invisible. Fix the producer.
- **Do NOT silence the logs.** They are useful; `gitio`/`process` tracing is
  load-bearing for debugging elsewhere. Route them to stderr, do not delete
  them.
- **Do NOT special-case only the `agent env` subcommand's own log line.** The
  pollution comes from the shared `gitio`/`process` logging that any code path
  can emit. The guarantee needed is "this subcommand's STDOUT contains only
  shell", not "these three known messages are suppressed".
- **Do NOT change what the export block contains.** `agent_env_exports` is
  correct; only the channel is wrong.

## Acceptance criteria

1. (MUST FAIL FIRST) `eval "$(uv run frob agent env <worktree>)"` succeeds with
   no filtering and sets FROB_WORKTREE, FROB_AGENT, and (under fleet context)
   PYTEST_XDIST_AUTO_NUM_WORKERS. Fails today with a bash syntax error.
2. `frob agent env <worktree>` stdout contains ONLY `export ` lines -- assert
   on every line, not just that the exports are present.
3. MUST-STILL-PASS CONTROL: the diagnostics still appear on stderr, unchanged.
   A fix that drops them trades one defect for another; verify they are
   redirected, not removed.
4. The no-fleet-context case still emits no bound (T-2221's control) and still
   produces valid, eval-able output.
5. `docs/guides/agent-playbook.md:243` documents the form that actually works.

## Scope note

`src/frob/app/agent_runner.py` is the `agent env` consumer of
`agent_env_exports` (line ~60). Whether the fix belongs there or in the shared
logging configuration is the implementer's call -- state which and why. If the
right fix is repo-wide (any stdout-emitting subcommand), say so and scope it
deliberately rather than widening silently.

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
