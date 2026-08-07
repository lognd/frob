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
---
Recurring dispatch friction, 4 occurrences in one session (T-0554, T-0261, T-0435, T-0609 agents): a full frob check / --stamp-baseline run exceeds the 120s agent foreground cap, the harness auto-backgrounds it, the sub-agent ends its turn waiting for a notification that can never reach it (playbook 3b), and the mission stalls until a coordinator manually pokes it. The playbook documents the anti-pattern but agents keep tripping because there is no sanctioned fast path. Provide one: either (a) a "frob check --stage NAME" chunked invocation where each stage reliably completes under ~90s so agents can loop stages in-foreground, or (b) a "--budget SECONDS" mode that runs as many gates as fit and reports the remainder as explicitly-not-run, or (c) make --stamp-baseline itself incremental. Update the agent playbook section 3b/6 with the sanctioned invocation once it exists. Related but distinct: T-0581 (process-pool parallelism), T-0582 (perf re-measurement), T-0584 (PRE001 sweep timeout).