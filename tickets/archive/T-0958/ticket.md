---
id: T-0958
title: reconcile the 56 deferred:T-0331 system-design entries against the landed REL26x-REL38x
  obligation families
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/system-design.yaml
- tests/test_registry_reconciliation_system_design.py
- src/frob/gates/__init__.py
- src/frob/strata/_distributed_txn.py
- src/frob/strata/_delivery_semantics.py
- src/frob/strata/_retry.py
- src/frob/strata/_reliability.py
- src/frob/strata/_backpressure.py
- src/frob/strata/_observability.py
- src/frob/strata/_slo.py
- src/frob/strata/_clock_ordering.py
- src/frob/strata/_message_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_distributed_txn.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_delivery_semantics.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_retry.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_backpressure.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_observability.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_slo.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_clock_ordering.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_message_schema.py
  reason: handled_by dispositions in system-design.yaml need (a) frob:enforces edges
    in the owning REL2xx/REL3xx rule modules (REG008) and (b) the corresponding rule
    ids registered in gates/__init__.py's _KNOWN_GATE_RULES (REG002), same listing-omission
    class T-0903/T-0923/T-0924 already fixed for other batches
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
designated_repro_test: null
acceptance:
- text: given the 56 rows, when the registry gate runs, then zero rows cite T-0331
    and every disposition resolves (REG002/REG008/REG011 clean)
  evidence:
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
  - tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
  - tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
- text: T-0756 new-gate-rule fixture proof -- before this change, TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
    FAILed (REG002 dangling handled_by:REL200/REL220/REL221/REL260/REL270/REL272/REL280/REL320/REL330/REL350/REL370,
    none of those ids were in gates/__init__.py's _KNOWN_GATE_RULES yet); after adding
    them alongside the matching handled_by dispositions and frob:enforces edges, the
    same production `registry_gate` invocation PASSes with zero violations
  evidence:
  - tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
threat: null
component: null
---
Successor to epic T-0331 (closing). The epic landed thirteen obligation families (REL26x backpressure through REL38x starvation, plus SYS204 contention). The 56 registry entries that deferred to the epic must now be re-dispositioned individually: handled_by:<rule> where a landed family genuinely covers the concept (with the frob:enforces edge REG008 wants), deferred to a real follow-up ticket for concepts still unbuilt, or reasoned out_of_scope per the T-0722/T-0912 precedents. Catalogued-is-not-enforced applies: no handled_by without a live registered rule.