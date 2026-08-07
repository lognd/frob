---
id: T-0150
title: 'self-conformance: vet capability scan of our own source must match design/frob.strata
  interfaces'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/app/__main__.py
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- frob.toml
- tickets.md
- tests/golden/frob_export_seccomp.json
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_fires
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_discharges_once_observed
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_discharges_once_mapped
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
frob vet already introspects dependencies for capability use (scan_directory_capabilities in src/frob/vet/_capability.py: exec/eval/network/fs/... per-language token scan). Point that same machinery at OUR OWN src/ tree and reconcile against the self-hosted strata design, so the interfaces recorded in design/frob.strata are provably in sync with what the code actually does. Reuse scan_directory_capabilities READ-ONLY (import it; do not modify src/frob/vet -- T-0147 is concurrently editing that package). Mechanism: a node-to-source-path mapping (investigate whether the kernel/surface already supports binding a node to a code path; if not, add the smallest principled mapping -- e.g. a [tool.frob]/frob.toml table or a strata clause -- and document the decision). Conformance rules, all loud (vacuous-pass doctrine): (1) capability observed in a mapped path but not declared on the mapped node = violation (undeclared interface); (2) capability declared on a node with zero observed sites in its mapped paths = violation (stale design); (3) source directories under src/ with no node mapping = violation (unmodeled code), no silent exemption; test paths excluded per _is_test_path precedent. Surface as a new SYS-family gate rule id wired into frob sys audit (follow the THREAT/SYS rule registration precedent) and run against design/frob.strata in our own gates. Expect the first honest run to FAIL until design/frob.strata is updated to declare reality -- updating the design to match observed capabilities (or waiving with written reasons) is part of this ticket. Tests: fixture design+source trees for each rule firing and discharging; drift-lock so an unmapped capability kind in the scanner vocabulary fails loudly rather than being silently ignored.