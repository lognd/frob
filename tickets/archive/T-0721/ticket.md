---
id: T-0721
title: implement checkable-control enforcement for SC-* supply-chain registry entries
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/supply-chain.yaml
- tests/test_registry_reconciliation_supply_chain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_supply_chain.py
  reason: verification test for the registry reconciliation this ticket performs,
    same file T-0389 (the original SC-* reconciliation ticket) scoped for evidence
    binding
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_supply_chain.py::TestExhaustivenessGateOverRealSupplyChain::test_no_supply_chain_violations
designated_repro_test: null
threat: null
component: null
---
Standing home for the 39 supply-chain.yaml entries whose controls previously carried deferred:T-0389 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0389 closed; T-0389's pass re-pointed them here. Each entry needs either a real enforcing check in src/frob/vet/ (then flip to handled_by) or a reasoned out_of_scope disposition (many require external network/registry data -- checkability tag requires-external-data -- and are legitimate deferrals to future external-data-fetching work, not silent drops).