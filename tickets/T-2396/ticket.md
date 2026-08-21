---
id: T-2396
title: the shared-root write guard fires at commit time, after the damage is done
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- .claude/settings.json
- .claude/hooks/sync-claude-config.py
- docs/guides/claude-hooks.md
- tests/test_hook_root_write_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/root-write-guard.py
  reason: edit-time refusal hook needs its script, wiring, sync registration, docs,
    and its own test
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .claude/settings.json
  reason: edit-time refusal hook needs its script, wiring, sync registration, docs,
    and its own test
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: edit-time refusal hook needs its script, wiring, sync registration, docs,
    and its own test
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: edit-time refusal hook needs its script, wiring, sync registration, docs,
    and its own test
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_hook_root_write_guard.py
  reason: edit-time refusal hook needs its script, wiring, sync registration, docs,
    and its own test
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_hook_root_write_guard.py::test_agent_context_write_to_root_is_refused
- tests/test_hook_root_write_guard.py::test_worktree_fact_alone_is_sufficient_without_frob_agent
- tests/test_hook_root_write_guard.py::test_ledger_paths_are_exempt_even_for_an_agent
- tests/test_hook_root_write_guard.py::test_frob_land_internal_exempts_an_agent_write
- tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_for_an_agent
- tests/test_hook_root_write_guard.py::test_coordinator_or_human_write_to_root_is_allowed
- tests/test_hook_root_write_guard.py::test_fake_frob_worktree_value_does_not_satisfy_the_fact_check
- tests/test_hook_root_write_guard.py::test_agent_write_inside_its_own_worktree_is_allowed
- tests/test_hook_root_write_guard.py::test_non_guarded_tool_is_ignored
designated_repro_test: null
acceptance:
- text: Given an agent with a worktree, when it attempts to WRITE a file in the shared
    root, then the write is refused at edit time and it is pointed at frob ticket
    work, before the root is dirtied.
  evidence:
  - tests/test_hook_root_write_guard.py::test_agent_context_write_to_root_is_refused
  - tests/test_hook_root_write_guard.py::test_worktree_fact_alone_is_sufficient_without_frob_agent
  - tests/test_hook_root_write_guard.py::test_ledger_paths_are_exempt_even_for_an_agent
  - tests/test_hook_root_write_guard.py::test_frob_land_internal_exempts_an_agent_write
  - tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_for_an_agent
- text: Given the coordinator or a human editing the shared root legitimately, when
    they write, then the guard does not fire, proving the discriminator discriminates
    in both directions.
  evidence:
  - tests/test_hook_root_write_guard.py::test_coordinator_or_human_write_to_root_is_allowed
  - tests/test_hook_root_write_guard.py::test_fake_frob_worktree_value_does_not_satisfy_the_fact_check
  - tests/test_hook_root_write_guard.py::test_agent_write_inside_its_own_worktree_is_allowed
  - tests/test_hook_root_write_guard.py::test_non_guarded_tool_is_ignored
threat: null
component: hooks
anchor: false
anchor_reason: null
land_commit: 2e33cc71767f3d5e357675e22aae1f78fa5b5360
---
MEASURED TODAY: two agents in one wave edited the SHARED ROOT instead of
their worktree, and a third agent's land was DirtyMain-blocked as a
result. This has now recurred across multiple waves and is one of the
most expensive recurring failures in the drive, because it blocks every
OTHER agent, not just the one that erred.

The existing `FROB_AGENT` git hook guards COMMIT time. The damage starts
at EDIT time: by the time a commit is attempted, the shared root is
already dirty and every concurrent land is already refusing. The guard
is correctly placed for the action it names and too late for the
failure it is meant to prevent.

FIX: a PreToolUse-style hook that refuses a WRITE to the shared root
when `FROB_AGENT` is set, pointing the agent at `frob ticket work`
instead. Two things it must get right:
  - It has to fire on the EDIT, not the commit -- that is the entire
    point.
  - It must not block the coordinator or a human, who legitimately edit
    the root. `FROB_AGENT` is the available discriminator, but note it
    has been MEASURED UNSET in Agent-tool shells before (see the T-2071
    comment in `_WORKTREE_LEASE_HOOK_SCRIPT`, which added a second
    FACT-based guard for exactly that reason). So do not rely on
    `FROB_AGENT` alone -- pair it with a fact-based signal such as
    whether a worktree exists for an in-progress ticket owned by this
    process. Verify the discriminator actually discriminates before
    shipping; a guard that never fires and a guard that always fires are
    equally useless, and this repo has shipped both.