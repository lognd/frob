---
id: T-1809
title: Gate Claude-config sync drift in frob check (T-1719 item 2)
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/check_runner.py
- tests/test_check_runner.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrowing package glob to the specific files this ticket touches, per ticket
    start's over-broad-scope refusal
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/check_runner.py
  reason: T-1937 holds a live cross-worktree lease on gates/__init__.py and gates/_waive.py,
    blocking the gates-pipeline wiring path this ticket originally planned; check_runner.py
    already documents (deploy-drift/deploy-conformance) the identical escape valve
    for exactly this scope conflict -- an extra CheckResult stage outside frob.gates's
    job table, same gate-shaped fail-frob-check semantics
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md is contested by concurrent in-progress T-1881's live
    lease; documenting the new check stage in check_runner.py's own module/function
    docstrings instead (matches the deploy-drift/deploy-conformance precedent, which
    also documents itself locally rather than in gates.md since it too sits outside
    frob.gates's own scope)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_check_runner.py
  reason: test coverage for the new claude-config-drift check_runner stage
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: 'AFFECT001: _claude_config_drift_result''s affects()-closure doc target
    is this page'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_managed_copy_absent
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_clean_when_in_sync
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_no_stage_when_repo_has_no_managed_config
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1719 item 2 (gate the Claude-config drift) was cut from that ticket's
own scope for two reasons: (a) it depends on the sync verb the sibling
follow-up ticket implements first (there is nothing to gate a `--check`
call against until the verb exists), and (b) `docs/modules/gates.md` and
the `_KNOWN_GATE_RULES` registry it documents were explicitly off-limits
during T-1719's dispatch window (held by other concurrent agents working
T-1773/T-1735/T-1781).

Once the sync-verb follow-up lands, add a rule (register a real, free
rule id in the `_KNOWN_GATE_RULES` registry and `docs/modules/gates.md`
-- do not invent an unregistered id) that fails `frob check` when a
managed file (per the verb's own manifest) differs from its materialized
`~/.claude/` copy. Wire it as its own `--check`-shaped gate stage,
following the existing `gate:*` family pattern in `src/frob/gates/`.