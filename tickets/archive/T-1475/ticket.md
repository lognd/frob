---
id: T-1475
title: 'main suite: last 2 failures blocking green'
state: done
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/gates/**
- tests/test_registry_exhaustiveness.py
- tests/unit/strata/test_mutation_audit.py
- src/frob/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
designated_repro_test: null
threat: null
component: null
---
Two failures block a green main suite run:

1. tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
   REG008 findings on docs/design/registry/check-coverage.yaml. Recent lands
   added CHK-GATE-NEGEXIST001/CHK-GATE-SYS107 entries that presumably lack
   whatever REG008 demands. Fix by satisfying REG008 honestly for the new
   entries, matching sibling entries' compliance.

2. tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
   Pre-existing failure: the mutation-audit second detector's
   disclosed-gaps set drifted, an extra 'env.read' gap appeared
   (downstream of the 2026-08-02 env-mode-explosion and T-1453 via
   migration). Determine whether env.read is a genuine new app-level gap
   the detector cannot see (update disclosed-gaps allowlist with honest
   reason) or a spurious drift (fix the detector/join instead).