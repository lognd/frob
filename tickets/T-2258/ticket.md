---
id: T-2258
title: 'frob ticket work never surfaces the fleet env, so T-2221''s xdist bound is
  never applied: an agent ran 39 unbounded processes while the box sat at 1GB free
  RAM'
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
- src/frob/app/ticket_runner/_lifecycle.py
evidence_scope:
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
- tests/test_ticket_work_and_land_finish.py::TestWork::test_fleet_context_reports_the_bound_agent_env_exports_computed
- tests/test_ticket_work_and_land_finish.py::TestWork::test_no_fleet_context_does_not_claim_an_xdist_bound
- tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
- tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
acceptance:
- text: 'frob ticket work output includes the exact command (or export block) to apply
    the fleet env, naming the resolved worktree path (fails today: zero references
    to ''agent env'' under src/frob/app/ticket_runner/)'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
- text: Values come from agent_env_exports, not a second computation
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_fleet_context_reports_the_bound_agent_env_exports_computed
- text: 'MUST-STILL-PASS: with no other live lease, no bound is claimed and solo worktree
    creation is unchanged'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_no_fleet_context_does_not_claim_an_xdist_bound
- text: ticket work exit code and existing behaviour unchanged; additive output only
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
- text: State whether other worktree-creating paths should emit it too; do not widen
    silently
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d21d2570d092c0ddde4088a577832a72b984e6e0
---
# T-2221's xdist bound is never applied: `frob ticket work` creates the worktree, knows the env, and never surfaces it -- agents run unbounded and drove the box to 1GB free RAM

## Measured evidence (2026-08-16)

T-2221 landed `agent_env_exports` (`src/frob/tickets/_worktree_guard.py`), which
correctly computes a fleet-aware bound. With 7 live leases:

    $ uv run frob agent env .claude/worktrees/t-2243
    agent env: fleet context detected -> PYTEST_XDIST_AUTO_NUM_WORKERS=1
    export FROB_WORKTREE=...
    export FROB_AGENT=1
    export PYTEST_XDIST_AUTO_NUM_WORKERS=1

**Nothing applies it.** `frob ticket work` -- the command that creates the
worktree and is the FIRST thing every dispatched agent runs -- never mentions
`agent env`:

    git grep -nE "agent env|agent_env_exports|export FROB" \
      -- src/frob/app/ticket_runner/     ->  no matches

The only mandate is a playbook line (`docs/guides/agent-playbook.md:243`). So a
bound that exists, is correct, and is computed on demand depends entirely on
each agent remembering to run `eval "$(frob agent env <worktree>)"`.

**Measured consequence.** An agent dispatched AFTER T-2221 landed was running
~39 live processes in its worktree -- the signature of `pytest -n auto`
resolving to all 12 CPUs -- while the machine sat at:

    Mem:   23 total, 16 used, 1 free, 4 buff/cache, 6 available
    Swap:  24 total,  6 used

1GB free RAM, 6GB swapped, load 25.9, with several agents each holding
700MB-1.4GB `frob check` processes. This repo has already lost a session to the
OOM killer under this condition. I had to interrupt a working agent mid-ticket
and ask it to run the eval by hand -- a manual workaround for a bound the
tooling already knows how to compute.

## Why the playbook line is not the fix

It is written down, at `agent-playbook.md:243`, and every dispatched agent is
told to read the playbook first. It still did not happen -- including for
agents I dispatched myself after T-2221 landed, because I illustrated the rule
in briefs with a different command. A rule that must be recalled at the right
moment, by every agent, on every dispatch, is not enforcement. The command that
CREATES the worktree already knows the worktree path and the fleet size; it is
the one place that cannot forget.

## Do NOT fix it this way

- **Do NOT have `frob ticket work` mutate the caller's environment.** A
  subprocess cannot export into its parent shell. Print the export block (or
  the exact `eval` line) so the agent can apply it -- surfacing, not magic.
- **Do NOT put the bound only in frob's own subprocess spawns.** Agents run
  `uv run pytest` directly from their shell; a fix that only covers
  frob-internal invocations misses the case that caused this.
- **Do NOT compute a different bound here.** `agent_env_exports` already owns
  that logic and its zero-other-leases control. Call it; do not reimplement it
  (two homes for one rule is the T-1966 shape).
- **Do NOT make this a hard requirement that fails `ticket work`.** Worktree
  creation must keep working for a solo developer with no fleet context.

## Acceptance criteria

1. (MUST FAIL FIRST) `frob ticket work <id>` output includes the exact command
   the agent must run to apply the fleet env (or the export block itself),
   naming the resolved worktree path. Fails today: zero references to
   `agent env` anywhere under `src/frob/app/ticket_runner/`.
2. The values shown come from `agent_env_exports`, not a second computation.
3. MUST-STILL-PASS CONTROL: with no other live lease, the output does not claim
   a bound that does not apply -- `agent_env_exports` already exports nothing in
   that case, and `ticket work` must not invent one. A solo developer's
   worktree creation is unchanged.
4. `ticket work`'s exit code and existing behaviour are unchanged; this is
   additive output only.
5. State whether the guidance is also worth emitting from any other
   worktree-creating path, and if so which -- do not widen silently.

## Scope note

`frob ticket work` lives in `src/frob/app/ticket_runner/_lifecycle.py`.
`agent_env_exports` lives in `src/frob/tickets/_worktree_guard.py` and is
consumed today only by `src/frob/app/agent_runner.py:60`. Read that consumer
before wiring a second one.