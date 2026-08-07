---
id: T-0722
title: implement SYS/REL checkable-control enforcement for the 49 unresolved system-design
  registry entries
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/design/registry/system-design.yaml
- tests/test_registry_reconciliation_system_design.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_system_design.py
  reason: 'frob.graph has no grammar for .yaml (confirmed: "no grammar registered
    for

    extension ''.yaml''" at check time), so system-design.yaml carries no symbol

    nodes a TESTS edge could bind to -- Route 1 of evidence_covers_scope

    (frob.gates.evidence_covers_scope) is structurally unreachable for a

    data-only registry-file scope on a non-docs-kind ticket. Adding the real,

    already-existing pin test file directly to scope (Route 2: evidence id''s

    own file is inside ticket.scope) is the same ad-hoc precedent

    tests/test_registry_reconciliation_system_design.py''s own header comment

    already documents for T-0424/T-0384..T-0390''s sibling reconciliation

    tickets; no source outside the declared registry-YAML work is touched.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile::test_is_in_registry_files
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile::test_loads_without_error
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile::test_no_malformed_entries
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
designated_repro_test: null
threat: null
component: null
---
Standing home for the 49 system-design.yaml entries whose controls previously carried deferred:T-0392 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0392 closed; T-0392's pass re-pointed them here. Each entry needs either a real enforcing SYS2xx/REL2xx check in src/frob/strata/ (then flip to handled_by) or a reasoned out_of_scope/duplicate_of disposition. Related to the T-0331 systems-checks epic and its T-0658 N:M coverage close condition (which is itself blocked by T-0392) -- once this ticket's entries get real checks, T-0658's coverage math should account for them the same way it accounts for the T-0331-deferred 56.