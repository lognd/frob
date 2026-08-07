---
id: T-0912
title: reword 14 legacy manifest-extraction-artifact dispositions to satisfy REG011
  in system-design.yaml
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/system-design.yaml
- tests/test_registry_reconciliation_system_design.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_system_design.py
  reason: 'frob.graph has no grammar for .yaml, so system-design.yaml carries no symbol
    nodes a TESTS edge could bind to -- adding the existing pin test file directly
    to scope (Route 2: evidence id''s own file is inside ticket.scope), same precedent
    T-0722 used; no source outside the declared registry-YAML work is touched'
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
designated_repro_test: null
threat: null
component: null
---
tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
asserts registry_gate() returns zero violations for system-design.yaml. It
was already red before T-0722 (verified against the pre-T-0722 file state):
the 14 pre-existing manifest-extraction-artifact entries (T-0392's original
pass) use disposition out-of-scope(manifest-extraction-artifact), whose bare
reason ("manifest-extraction-artifact") names no catching rule/CWE id and is
not a substantive "none -- <explanation>" reasoned-none disclosure per T-0680's
REG011 check -- so each fires a REG011 WARN. WARN severity means frob check
itself stays green, but this file's own stricter == [] pytest assertion does
not tolerate any violation, warn or error. T-0722 deliberately left these 14
untouched (out of its own declared 49-entry scope) and used a substantive
"none -- ..." reasoned-none phrasing for its own out-of-scope entries instead,
which does NOT trigger REG011. Fix: reword the 14 pre-existing entries'
disposition strings to a substantive out_of_scope:none -- <explanation> reason
(same shape T-0722 used), or waive REG011 there with a reasoned frob:waive if
the bare token is intentionally kept as a distinct "artifact" marker.