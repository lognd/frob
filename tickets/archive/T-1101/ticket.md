---
id: T-1101
title: 'vet: add 11 frob:enforces SC-* edges at the VET emitting sites + close the
  17-entry REG010 VET-family check-coverage gap (T-1087 follow-up)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_typosquat.py
- src/frob/vet/_scan.py
- src/frob/vet/_osv.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
- tests/test_vet.py::TestTyposquat::test_requets_flags_requests
- tests/test_vet.py::TestOsvAdapter::test_run_osv_scan_none_when_binary_absent
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_flags_undeclared_capability
designated_repro_test: null
acceptance:
- text: given the 11 SC-* entries T-1087 flipped to handled_by VET-family rules, when
    REG008 runs, then every one carries a frob:enforces edge at the real emitting
    site and REG010 reports zero missing VET-family CHK-GATE entries
  evidence:
  - tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
threat: null
component: null
---
Refile of T-1087's dead draft T-1101 (splice-race casualty, pre-T-1090). No src/frob/gates wrapper re-emits VET-family violations, so the enforces edges belong at the vet emitters themselves; also files the 17 missing CHK-GATE-VET* check-coverage entries (REG010).