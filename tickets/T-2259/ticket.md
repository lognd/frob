---
id: T-2259
title: frob agent env writes gitio/process diagnostics to STDOUT, so the documented
  eval fails with a bash syntax error -- T-2221's xdist bound has been inert fleet-wide
  since it landed
state: queued
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
- docs/modules/app.md
- tests/test_worktree_guard.py
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
designated_repro_test: null
acceptance:
- text: 'eval "$(uv run frob agent env <worktree>)" succeeds with NO filtering and
    sets the three vars (fails today: bash syntax error)'
  evidence: []
- text: stdout contains ONLY export lines -- assert on every line, not just that exports
    are present
  evidence: []
- text: 'MUST-STILL-PASS: the gitio/process diagnostics still appear, on stderr, unchanged
    -- redirected not removed'
  evidence: []
- text: No-fleet-context case still emits no bound and still produces valid eval-able
    output
  evidence: []
- text: agent-playbook.md:243 documents the form that actually works
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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
