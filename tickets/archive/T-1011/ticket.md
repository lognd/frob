---
id: T-1011
title: auto-sync check-coverage gate_rule_entries at land + generate command tables
  from argparse registry
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-1008
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/**
- docs/**
- tests/**
- src/frob/gates/_docblocks.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: T-1011(b) implements DOC005 freshness check + generator inside frob.gates._docblocks
    (docs/audits/coordination-churn.md item 3 sibling deliverable)
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_sorts_rows_across_sources
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_no_config_is_none
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_replaces_only_the_marked_block
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_no_markers_returns_false
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_flags_stale_generated_block
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_passes_after_sync
- tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_sync_commands_writes
designated_repro_test: null
acceptance:
- text: given a land whose diff adds a gate rule id, when it lands, then check-coverage.yaml
    carries the new row with no manual sync; given a new CLI subcommand, docs sync
    regenerates both tables and DOC005 verifies freshness
  evidence:
  - tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
  - tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_passes_after_sync
threat: null
component: null
---
Children 3+4 of T-1008 (bundled: both are generate-at-the-source items). (a) land runs the existing registry --sync-gate-rules automatically when _KNOWN_GATE_RULES changed in the landing diff, ending manual re-syncs (drifted twice this drive). (b) README and docs/modules/cli.md command tables become generated from the live argparse registry (frob docs sync-commands or equivalent), turning DOC005 from a hand-sync lock into a generator-freshness check.