---
id: T-0560
title: Schedule the pessimistic-auditor loop to auto-file concern_family_entries in
  check-coverage.yaml
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/
- src/frob/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_staleness.py::TestMissingGateRuleIds::test_finds_rules_with_no_entry
- tests/test_registry_staleness.py::TestMissingGateRuleIds::test_fully_covered_is_empty
- tests/test_registry_staleness.py::TestMissingGateRuleIds::test_unreadable_file_is_empty
- tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_appends_every_missing_rule
- tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_already_in_sync_returns_empty_tuple
- tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_missing_file_rejected
- tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns
- tests/test_registry_staleness.py::TestReg010Gate::test_fully_covered_no_reg010
designated_repro_test: null
threat: null
component: null
---
Split out of T-0424: the registry MODEL + honest seed is built (check-coverage.yaml, REG001-007 enforced), but the CONTINUOUS half of T-0424's acceptance ("the pessimistic-auditor loop runs on a schedule and its findings auto-file as dispositioned entries") is a real scheduling/automation feature -- a recurring driver plus an auditor-output-to-YAML writer -- not built in T-0424's pass. This ticket is that follow-up: wire a scheduled (or CI-triggered) pessimistic-auditor run whose findings append new dispositioned concern_family_entries rows to check-coverage.yaml automatically, so new gaps are found before the user notices them, per T-0424's root-cause charter.