---
id: T-0962
title: 'static checks: ABI/ISA compat-window stability + boot-chain signed/measured
  attestation obligations'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_supply_chain_boot.py
- docs/strata/reliability.md
- src/frob/strata/__init__.py
- tests/unit/strata/test_supply_chain_boot.py
- src/frob/gates/__init__.py
- docs/design/registry/system-design.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/__init__.py
  reason: 'Ticket scope only listed src/frob/strata/_supply_chain_boot.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was dispatched to follow (mirroring T-0646/T-0919/T-0960) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py, and registering the

    new rule ids in src/frob/gates/__init__.py''s _KNOWN_GATE_RULES (so

    REG002 can resolve handled_by:REL39x references). Widening to match

    T-0646/T-0919/T-0960''s own declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/strata/test_supply_chain_boot.py
  reason: 'Ticket scope only listed src/frob/strata/_supply_chain_boot.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was dispatched to follow (mirroring T-0646/T-0919/T-0960) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py, and registering the

    new rule ids in src/frob/gates/__init__.py''s _KNOWN_GATE_RULES (so

    REG002 can resolve handled_by:REL39x references). Widening to match

    T-0646/T-0919/T-0960''s own declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Ticket scope only listed src/frob/strata/_supply_chain_boot.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was dispatched to follow (mirroring T-0646/T-0919/T-0960) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py, and registering the

    new rule ids in src/frob/gates/__init__.py''s _KNOWN_GATE_RULES (so

    REG002 can resolve handled_by:REL39x references). Widening to match

    T-0646/T-0919/T-0960''s own declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/system-design.yaml
  reason: 'Ticket scope only listed src/frob/strata/_supply_chain_boot.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was dispatched to follow (mirroring T-0646/T-0919/T-0960) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py, and registering the

    new rule ids in src/frob/gates/__init__.py''s _KNOWN_GATE_RULES (so

    REG002 can resolve handled_by:REL39x references). Widening to match

    T-0646/T-0919/T-0960''s own declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_compiled_artifact_node_without_compat_window_fires
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_discharged_and_non_compiled_artifact_nodes_clean
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_waiver_discharges_finding
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_boot_chain_stage_node_without_attestation_fires
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_discharged_and_non_boot_chain_stage_nodes_clean
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_waiver_discharges_finding
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
threat: null
component: null
---
Filed while reconciling T-0958's system-design.yaml deferred rows. SDC-13-A-DECLARED-ABI-ISA-TARGET-IS-STABLE-ACROSS-A-COMPATIBILITY-WINDOW-A-COMPILED-ARTIFA and SDC-13-EVERY-BOOT-CHAIN-STAGE-IS-SIGNED-SECURE-BOOT-OR-MEASURED-INTO-AN-ATTESTABLE-LOG-MEA name two genuinely checkable, currently-unbuilt supply-chain/OS obligations: (1) a declared ABI/ISA compatibility-window claim on a compiled artifact that a static check could verify stays honored across the window, and (2) each boot-chain stage being signed (secure boot) or measured into an attestable log, again a presence/provenance claim a static grammar attr + proof check could enforce, mirroring the REL2xx/REL3xx PROVABILITY CONSTRAINT pattern (_obligation_proof.py::node_has_bound_code) already established for other obligation families. No landed REL/SYS family covers either concept today. Scope: a new strata rule module (e.g. src/frob/strata/_supply_chain_boot.py) plus docs/strata/reliability.md (or a new supply-chain doc section) plus the corresponding registry re-disposition once built.