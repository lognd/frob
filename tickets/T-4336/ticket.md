---
id: T-4336
title: Make gate stage-group membership mandatory at declaration
state: done
kind: bug
origin: agent
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- tests/system/test_cli_check.py
- docs/commands/check.md
- docs/guides/agent-playbook-appendix.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/check.md
  reason: 'T-4336: keep the gate-declaration checklist and --only stage-group docs
    in sync with the new frob.gates._GATE_STAGE_GROUPS source of truth'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/guides/agent-playbook-appendix.md
  reason: 'T-4336: keep the gate-declaration checklist and --only stage-group docs
    in sync with the new frob.gates._GATE_STAGE_GROUPS source of truth'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-4336: keep the gate-declaration checklist and --only stage-group docs
    in sync with the new frob.gates._GATE_STAGE_GROUPS source of truth'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): T-4336 is a preventive/structural refactor
    of gate-declaration machinery: at HEAD every gate is already grouped (all 70 pass
    test_available_stages_cover_every_gate_and_tool both before and after), so there
    is no currently-failing runtime defect to reproduce fail-then-pass. The fix makes
    a FUTURE omission impossible to express (an import-time assert), it does not change
    today''s --only behavior for any existing gate -- proven by test_gate_stage_group_migration_is_byte_identical''s
    byte-identical-mapping assertion.'
  actor: logan
  at: '2026-09-08'
  old_length: 2643
  new_length: 3194
evidence:
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
- tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical
- tests/system/test_cli_check.py::TestCheckStageGroups::test_stage_group_expands_like_hand_listed_only
designated_repro_test: null
acceptance:
- text: given a gate registered in frob.gates._ALL_GATES without a stage-group assignment,
    when frob is imported/invoked (including a selective --only run), then it fails
    loudly at load time instead of silently passing every check
  evidence:
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_stage_group_expands_like_hand_listed_only
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED: src/frob/check/__init__.py's _STAGE_GROUPS (around line 1215) carries EIGHT separate comment blocks, each documenting the identical recurring defect -- a gate registered in frob.gates._ALL_GATES but never added to a _STAGE_GROUPS member, most recently T-4307 (land_format), which failed CI earlier today. An ungrouped gate still passes its own unit tests and still runs under a full unscoped invocation, so it looks healthy everywhere except the selective --only paths people invoke day to day, where it silently never runs.

ASK: make stage-group membership part of DECLARING a gate so omitting it is impossible to express, not merely detected after the fact by a test (tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool, which only catches this when the full suite runs). Read how gates are declared today before committing to a shape -- frob.gates.__init__ already has a working precedent for this exact pattern (_CANONICAL_GATE_ORDER: a second declaration next to _ALL_GATES, closed by a module-level assert that fires at import time, i.e. on every invocation including scoped ones).

CONSTRAINTS:
- Group membership is not arbitrary: it tracks real execution properties (diff-scoped vs not; process-pool vs thread-pool, i.e. frob.gates._PROCESS_POOL_GATES). Whatever shape is chosen must still express those, and a gate must still be able to sit in more than one group (not used today, but must stay expressible).
- PROVE the migration is behaviour-preserving: assert the full gate->groups mapping is byte-identical before and after, rather than eyeballing it.
- Keep tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool. Once membership is mandatory it should become impossible to fail -- say so in a comment where it lives so nobody deletes it later as redundant.

RELATED, do not duplicate: T-4329 landed the same class of fix for pytest's heavy-test grouping (fixture-closure derivation instead of a hand-maintained name list). T-4333 (queued) is the broader survey of hand-maintained membership lists repo-wide. This ticket is the concrete gate/stage-group instance only.

This is a refactor of live enforcement machinery -- land it on its own.

NOTE: this work was originally assigned as T-4313, but no such ticket exists anywhere in this repo's git history, tickets/, tickets/archive/, or any worktree -- only a stale .frob/tickets/T-4313.lock residue (T-4314-class leftover from an id-allocation attempt that never completed). Filed fresh under this id after exhaustive search found no T-4313 to resume; see Done report.

frob:no-behavior-change reason="T-4336 is a preventive/structural refactor of gate-declaration machinery: at HEAD every gate is already grouped (all 70 pass test_available_stages_cover_every_gate_and_tool both before and after), so there is no currently-failing runtime defect to reproduce fail-then-pass. The fix makes a FUTURE omission impossible to express (an import-time assert), it does not change today's --only behavior for any existing gate -- proven by test_gate_stage_group_migration_is_byte_identical's byte-identical-mapping assertion."