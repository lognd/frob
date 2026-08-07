---
id: T-0683
title: 'docs: state that the drift gate always evaluates regardless of --only/narrowed
  gate selection (T-0265 semantics)'
state: done
kind: docs
origin: agent
created: '2026-07-22'
priority: low
parent: T-0265
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only ticket; CLI-dispatch integration test is the bound evidence (T-0167
    precedent), scope-added for covers_scope (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN docs/modules/gates.md WHEN a reader checks --only semantics THEN the
    always-evaluated drift behavior is documented with the T-0265 rationale
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
T-0265 made _build_jobs fold drift into every run_gates call so narrowed selections agree with full runs (DRIFT002 is authoritative for edge-endpoint resolution). docs/modules/gates.md does not yet say drift always evaluates under --only; T-0265's reviewer flagged the doc gap. One short note under the --only description. Also note here for the record: the _run_combined_jobs ProcessPoolExecutor-inside-ThreadPoolExecutor fork hazard disclosed in T-0265's Done report is T-0581's territory (its redesign should eliminate it).