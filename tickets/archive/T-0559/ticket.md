---
id: T-0559
title: REF002 single-anchor pool triage (32 findings)
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002
- tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference
- tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001
- tests/test_refs_gate.py::TestTiers::test_two_refs_passes
designated_repro_test: null
threat: null
component: null
---
REF002 pool from `uv run frob check --only refs`: 32 single-inbound-
reference advisories (WARN, suggestion-severity per the module docstring)
across md/strata fixtures. Per finding: add a genuine second consumer
where one is natural (a doc cross-reference or a legitimate second call
site), or waive with an honest single-anchor-by-design reason following
the existing litmus-fixture waiver precedent already in this repo. No
fabricated consumers. Target: REF002 unwaived = 0, or a follow-up ticket
with the exact honest remainder.