---
id: T-1969
title: Register CLAUDE001 in _KNOWN_GATE_RULES (T-1809's gate registry entry)
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
- docs/modules/gates.md
evidence_scope:
- tests/test_check_runner.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_managed_copy_absent
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_clean_when_in_sync
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1809 implemented the Claude-config sync drift check (CLAUDE001,
`src/frob/app/check_runner.py::_claude_config_drift_result`) as an opt-in
extra `frob check` stage, following the DEPLOY001-003 precedent
(`_deploy_drift_result`/`_deploy_conformance_result`), because
`src/frob/gates/__init__.py` and `src/frob/gates/_waive.py` were both
under T-1937's live cross-worktree lease for the whole of T-1809's
dispatch window -- registering the rule id in `_KNOWN_GATE_RULES` was not
possible at that time.

T-1937 is now `done` and closed -- it is NOT a queue, so this cannot be
left "for T-1937 to pick up" as T-1809's own Done report originally
assumed. This ticket is the real, doable follow-up:

1. Add "CLAUDE001" to `_KNOWN_GATE_RULES` in `src/frob/gates/_waive.py`.
2. Document CLAUDE001 in `docs/modules/gates.md`'s rule catalog (the
   `claude-config-drift` stage, `src/frob/app/check_runner.py`), matching
   how DEPLOY001-003 are (or are not) documented there -- confirm the
   precedent before assuming a gates.md entry is even the right shape for
   a non-`frob.gates`-pipeline stage.
3. Verify `frob.tickets._new_gate_rule_acceptance`'s literal-scrape
   preflight now recognizes CLAUDE001 as a known rule id (this is the
   actual bug T-1937 fixed for 10 other ids -- CLAUDE001 landed one
   ticket later and was never swept into that fix).

Filed at medium (matching T-1808/T-1809's own priority) rather than a
lower "wire it up" priority -- per the coordinator's T-1960 finding that
under-prioritized "wire X into Y" follow-ups starve while their
higher-priority parents complete, so this stays visible in `frob ticket
doable` at the same weight as the work it completes.