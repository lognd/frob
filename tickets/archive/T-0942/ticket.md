---
id: T-0942
title: PARSE002 fires on graph-excluded paths where waivers cannot bind (broken.py
  fixture)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_parse_failures.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001: parse_failure_gate''s affects-closure doc'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestParseFailureGate::test_partial_parse_in_graph_excluded_path_is_silent
- tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation
designated_repro_test: null
acceptance:
- text: given tests/fixtures/lang/broken.py (graph-excluded, intentionally malformed),
    when the full frob check runs, then PARSE002 reports no finding for it while a
    partially-parsed NON-excluded file still fires PARSE002
  evidence:
  - tests/test_gates.py::TestParseFailureGate::test_partial_parse_in_graph_excluded_path_is_silent
  - tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation
threat: null
component: null
---
T-0940 added the gate-endorsed in-file frob:waive PARSE002 to tests/fixtures/lang/broken.py, but the waiver cannot bind: waivers attach through graph-ingested edges and tests/fixtures/** is excluded from frob.graph ingestion (same class T-0897 fixed for PII010/RENDER001/SEC-CVE by consulting frob.excludes directly). Fix: parse_failure_gate's PARSE002 path consults frob.excludes.is_excluded/load_exclude_globs and stays silent for excluded paths -- an excluded file contributes no symbols to the obligation graph, so 'symbols silently missing' is vacuous there. Keep PARSE002 firing for non-excluded files. Also correct the gate's remedy message to not recommend an in-file waive for excluded paths.