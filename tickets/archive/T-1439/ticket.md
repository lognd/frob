---
id: T-1439
title: Reclassify process-control registry entries (signal.signal, sys.exit/os._exit)
  out of capability kind env
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_registry.py
- src/frob/strata/_selfconform.py
- tests/test_capability_registry.py
- src/frob/vet/_capability_registry/_dangerous_ops_python.py
- src/frob/vet/_capability_registry/_kinds.py
- src/frob/vet/_capability_registry/_matrix.py
- src/frob/strata/_threat_catalog_benign.py
- docs/modules/vet.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry/_dangerous_ops_python.py
  reason: T-1420 split the monolithic _capability_registry.py into a package after
    the ticket was filed; scope glob predates the split
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/vet/_capability_registry/_kinds.py
  reason: T-1420 split the monolithic _capability_registry.py into a package after
    the ticket was filed; scope glob predates the split
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/vet/_capability_registry/_matrix.py
  reason: T-1420 split the monolithic _capability_registry.py into a package after
    the ticket was filed; scope glob predates the split
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/strata/_threat_catalog_benign.py
  reason: THREAT002 gate requires a BenignCapability excuse entry for the new kind
  actor: logan
  at: '2026-08-04'
- op: add
  glob: docs/modules/vet.md
  reason: AFFECT001 requires the affects()-closure doc to move with CAPABILITY_KINDS/CAPABILITY_MATRIX_EXCUSES
  actor: logan
  at: '2026-08-04'
- op: add
  glob: design/frob.strata
  reason: waive clause for T-1439 removed from design/frob.strata testsuite node once
    registry entries reclassified
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_excuse_kind_and_language_registered
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/test_capability_registry.py::TestNegativeFixtures::test_signal_signal_is_process_control_not_bare_env
designated_repro_test: null
acceptance:
- text: GIVEN a file calling signal.signal WHEN the capability scanner runs THEN the
    observation is a declarable kind, not bare env
  evidence:
  - tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_excuse_kind_and_language_registered
  - tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
  - tests/test_capability_registry.py::TestNegativeFixtures::test_signal_signal_is_process_control_not_bare_env
- text: GIVEN the registry no longer emits bare env WHEN the drift-lock tests run
    THEN _EXTENDED_KINDS no longer contains env and the testsuite waive clause is
    removed
  evidence:
  - tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_excuse_kind_and_language_registered
  - tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
threat: null
component: null
---
T-0771's env read/write split deliberately left 3 registry entries tagged capability_kind=env that are process-lifecycle/signal operations, not environment-variable access (its own Done report calls this a pre-existing kind-naming mismatch and promised a follow-up that was never filed -- this is it). Consequence, first hit 2026-08-02: may-env declarations now explode to env.read/env.write (WIRED_MODE_FAMILIES), so NO declaration can ever discharge a bare env observation; the first test that called signal.signal (tests/test_serve_socket.py, T-1378's kill-escalation child) turned SELFAUDIT001 SYS100 red on node testsuite with no honest declaration available, and a design waive clause is the only escape. Fix: move signal.signal (and the sys.exit/os._exit entries if they emit) to an accurate kind -- install-hook fits a process-wide signal handler's semantics, or introduce a process-control kind if not -- update matrix excuses and the TestExtendedKindsDriftLock disjointness lock, drop bare env from _EXTENDED_KINDS once no entry emits it, and remove the testsuite waive clause this incident added.