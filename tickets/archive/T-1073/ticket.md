---
id: T-1073
title: reconcile FAMILY_MODES 'proc' vs vet registry's 'exec' kind naming mismatch
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_modes.py
- src/frob/vet/_capability_registry.py
- tests/unit/vet/test_capability_modes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/vet/test_capability_modes.py
  reason: adding a litmus test for the PROC_FAMILY_SCANNER_KIND naming-reconciliation
    constant this ticket introduces
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/vet/test_capability_modes.py::TestProcFamilyNamingReconciliation::test_proc_family_kept_distinct_from_registry_exec_kind
designated_repro_test: null
threat: null
component: null
---
T-0771 found: frob.vet._capability_modes.FAMILY_MODES defines a 'proc' family (mode 'spawn') but src/frob/vet/_capability_registry.py has ZERO capability_kind='proc' entries -- every process-spawn signal is registered under the pre-existing, unrelated 'exec' kind instead. 'ffi' (mode 'call') IS a real registry kind (ctypes/cffi/ExtensionFileLoader) but like 'proc' has no tier-2 _KIND_MAP join. Decide: rename FAMILY_MODES's 'proc' to 'exec' for consistency with the registry (blast radius: CWE_CATALOG, DEFAULT_BENIGN_CAPABILITIES, docs, potentially sibling-repo declarations), OR keep 'proc' as a distinct future vocabulary and leave 'exec' alone. Either way this is a naming-vocabulary decision bigger than a needle-table extension, deliberately not forced into T-0771.