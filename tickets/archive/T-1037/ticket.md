---
id: T-1037
title: 'REG011 quality-bar drift: 798 out_of_scope reasons in weaknesses.yaml fail
  T-0680''s substantive-disclosure check'
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
- src/frob/gates/_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while closing epic T-0346: `tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations` fails on current main -- `registry_gate` reports 798 REG011 (WARN severity, T-0680: registry-YAML `out_of_scope:<reason>` quality check requiring a substantive reasoned-none disclosure, not a bare excuse) violations against `docs/design/registry/weaknesses.yaml` alone, out of 1157 total registry violations repo-wide.

Root cause: REG011 was added by T-0680, which landed after T-0384's reconciliation test was written and pinned "zero violations" against `weaknesses.yaml`. T-0384 never anticipated this new WARN-level quality bar. `weaknesses.yaml`'s `out_of_scope:` dispositions (presumably many of its CWE `out-of-scope-naming-the-missing-concept` entries, per T-0346's own acceptance criterion [1] wording) apparently do not meet REG011's substantive-reason bar.

This is a real, live gate warning (not an error) affecting a file this session did not touch. Two possible fixes, for the reviewer to choose: (1) improve the ~798 flagged `out_of_scope` reason strings in weaknesses.yaml to satisfy REG011's substantive-disclosure bar (real remediation, likely large), or (2) if the reasons are already substantive and REG011's heuristic is simply too strict for this file's phrasing convention, adjust REG011 or file targeted waivers. Scope: docs/design/registry/weaknesses.yaml, tests/test_registry_reconciliation_weaknesses.py, possibly src/frob/gates/_registry_exhaustiveness.py (REG011 itself) depending on the reviewer's chosen direction.

## Failure log
- 2026-07-28 attempt 1: already fixed by T-1019 before this wave (REG011 0 violations, ticket's own named regression test passes on current main); unrelated pre-existing test_every_deferred_entry_targets_an_open_ticket failure found and filed separately as T-1116

## Drop reason
- 2026-07-28: already fixed by T-1019 before this wave started -- REG011 measures 0 violations repo-wide and the ticket's own named regression test (test_no_weaknesses_violations) passes on current main; unrelated pre-existing failure found while verifying and filed separately as T-1116