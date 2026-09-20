---
id: T-0627
title: 'frob check: chunked/stage-wise invocation that stays under agent foreground
  caps'
state: done
kind: ux
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/app/check_runner.py
- docs/guides/agent-playbook.md
- tests/system/test_cli_check.py
- tests/system/conftest.py
- tests/unit/test_app_runners_batch6.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_cli_check.py
  reason: T-0627 needs CLI-level system tests for --only stage groups/list and FROB_AGENT
    refusal, unit tests for check_runner's refusal helper, conftest.py's env kwarg
    to exercise FROB_AGENT, and docs/commands/check.md (canonical command reference
    + available_stages' frob:doc anchor) documenting the --only stage-group vocabulary
    and refusal alongside the agent playbook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/conftest.py
  reason: T-0627 needs CLI-level system tests for --only stage groups/list and FROB_AGENT
    refusal, unit tests for check_runner's refusal helper, conftest.py's env kwarg
    to exercise FROB_AGENT, and docs/commands/check.md (canonical command reference
    + available_stages' frob:doc anchor) documenting the --only stage-group vocabulary
    and refusal alongside the agent playbook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: T-0627 needs CLI-level system tests for --only stage groups/list and FROB_AGENT
    refusal, unit tests for check_runner's refusal helper, conftest.py's env kwarg
    to exercise FROB_AGENT, and docs/commands/check.md (canonical command reference
    + available_stages' frob:doc anchor) documenting the --only stage-group vocabulary
    and refusal alongside the agent playbook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/commands/check.md
  reason: T-0627 needs CLI-level system tests for --only stage groups/list and FROB_AGENT
    refusal, unit tests for check_runner's refusal helper, conftest.py's env kwarg
    to exercise FROB_AGENT, and docs/commands/check.md (canonical command reference
    + available_stages' frob:doc anchor) documenting the --only stage-group vocabulary
    and refusal alongside the agent playbook
  actor: logan
  at: '2026-07-22'
body_changes:
- mode: append
  reason: condense --only preset grouping rationale into T-0627 body
  actor: logan
  at: '2026-09-19'
  old_length: 999
  new_length: 2358
evidence:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_only_list_prints_stages_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_bare_check_refuses_under_frob_agent
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stage_selected_check_runs_under_frob_agent
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_allow_full_check_override_bypasses_refusal
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_bare_check_unaffected_without_frob_agent
- tests/system/test_cli_check.py::TestCheckStageGroups::test_only_list_prints_stage_names
- tests/system/test_cli_check.py::TestCheckStageGroups::test_only_list_json_wraps_stages
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
- tests/system/test_cli_check.py::TestCheckStageGroups::test_stage_group_expands_like_hand_listed_only
- tests/system/test_cli_check.py::TestCheckAgentRefusal::test_bare_check_refuses_under_frob_agent
- tests/system/test_cli_check.py::TestCheckAgentRefusal::test_stage_selected_check_runs_under_frob_agent
- tests/system/test_cli_check.py::TestCheckAgentRefusal::test_allow_full_check_override_bypasses_refusal
- tests/system/test_cli_check.py::TestCheckAgentRefusal::test_bare_check_unaffected_without_frob_agent
designated_repro_test: null
acceptance:
- text: GIVEN a dispatched sub-agent in a fresh worktree WHEN it verifies a ticket
    using the documented invocation sequence THEN no single command exceeds 120s wall-clock
    on this repo AND full-gate coverage (or an explicit not-run list) is reported
  evidence:
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
  - tests/system/test_cli_check.py::TestCheckAgentRefusal::test_bare_check_refused_under_frob_agent
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Recurring dispatch friction, 4 occurrences in one session (T-0554, T-0261, T-0435, T-0609 agents): a full frob check / --stamp-baseline run exceeds the 120s agent foreground cap, the harness auto-backgrounds it, the sub-agent ends its turn waiting for a notification that can never reach it (playbook 3b), and the mission stalls until a coordinator manually pokes it. The playbook documents the anti-pattern but agents keep tripping because there is no sanctioned fast path. Provide one: either (a) a "frob check --stage NAME" chunked invocation where each stage reliably completes under ~90s so agents can loop stages in-foreground, or (b) a "--budget SECONDS" mode that runs as many gates as fit and reports the remainder as explicitly-not-run, or (c) make --stamp-baseline itself incremental. Update the agent playbook section 3b/6 with the sanctioned invocation once it exists. Related but distinct: T-0581 (process-pool parallelism), T-0582 (perf re-measurement), T-0584 (PRE001 sweep timeout).

<!-- narrative-moved:src/frob/check/__init__.py:1278:T-0627 -->
frob:ticket T-0627
: Named `--only` presets grouping related stages so an agent can budget one
: chunk of `frob check` per invocation instead of the full run (T-0627: a
: full `--only gates` pass on this repo measured ~113s wall time, over the
: ~120s agent foreground cap documented in `docs/guides/agent-playbook.md`
: section 3b -- past that cap the harness auto-backgrounds the command and
: a dispatched sub-agent stalls forever waiting on a notification that can
: never reach it). Membership names are tool names (this module's own
: `_TOOL_STAGES`) or gate names (`frob.gates._ALL_GATES`); `_resolve_only`
: expands a group alias into its members before doing its existing
: gate/tool split, so a group behaves exactly like hand-listing its
: members on `--only`. The gate-name split mirrors
: `frob.gates._PROCESS_POOL_GATES` (the CPU-bound gates dispatched to a
: process pool) vs. the thread-pool remainder: `gates-native`/
: `gates-security` each take a few of the CPU-bound giants (measured
: comfortably under the 90s per-stage target), `gates-fast` takes every
: cheap/I/O-bound gate (also well under budget on its own).
frob:ticket T-0788
frob:ticket T-0665
: `lint`/`static` name tools (this module's own `_TOOL_STAGES`), never
: gates, so they are safe to hand-list directly.