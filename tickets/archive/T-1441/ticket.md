---
id: T-1441
title: 'arch: LARGE001 splits of gates _sys and _dead_symbols (T-1420 delivered portion
  1)'
state: done
kind: feature
origin: agent
created: '2026-08-02'
priority: high
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/gates/_sys.py
- src/frob/gates/_sys_selfaudit.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_wire.py
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
- docs/strata/host.md
- src/frob/vet/_capability_registry.py
- src/frob/vet/_capability_registry/**
- src/frob/vet/_capability.py
- tests/test_capability_registry.py
- tests/test_vet.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry.py
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability_registry/**
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability.py
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_capability_registry.py
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_vet.py
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/gates/_waive.py
  reason: the t-1420 branch also carries the earlier-session T-1420 commit 8efc97e3
    (capability_registry package split, gate-verified as part of frob check --ticket
    T-1420 budget-100 clean run); this leaf lands the whole delivered branch, so its
    scope must cover that split too
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
- tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
designated_repro_test: null
acceptance:
- text: GIVEN the two split commits WHEN frob check --only archgate --only wire --only
    dead_symbols --only drift runs THEN 0 errors and LARGE001 no longer lists _sys.py
    or _dead_symbols.py
  evidence:
  - tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
  - tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
  - tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
  - tests/test_gates.py::TestSysGate::test_sys001_dangling
  - tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
threat: null
component: null
---
Leaf carrier for T-1420's first delivered portion (T-1414 precedent), so completed splits land on main while T-1420's lease continues on the remaining 50 files. Two verbatim-relocation splits, both gate-verified in the t-1420 worktree: (1) src/frob/gates/_sys.py 819 to 537 lines, SELFAUDIT001 family moved to new _sys_selfaudit.py; (2) src/frob/gates/_dead_symbols.py 819 to 216 lines, WIRE001/WIRE002 family moved to new _wire.py, frob.gates.__init__ repointed. Doc and frob:tests edges repointed in the same commits; WIRE001's T-1431 relocation-awareness held on both (no false fire). LARGE001 count 52 to 50.