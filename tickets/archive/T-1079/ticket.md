---
id: T-1079
title: 'strata: model tests/**, scripts/**, frob-core, strata-core in design/frob.strata
  or adopt reasoned exclusions (SYS103 264-finding follow-up)'
state: done
kind: security
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- docs/modules/strata.md
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
designated_repro_test: null
acceptance:
- text: given the SYS103 coverage-totality check runs repo-wide, when the modeled-or-excluded
    disposition lands, then SYS103 reports zero unbound capable modules without narrowing
    its own scan design
  evidence:
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
threat: null
component: null
---
Refile of T-0667's dead draft (T-0667 Done report cited a draft id that did not survive its land -- TICK006). SYS103's first full-tree measurement found 264 real unbound-module findings concentrated in tests/**, scripts/**, frob-core and strata-core sources; T-0667 scoped its shipped check to SYS102's existing footprint and documented the gap in docs/modules/strata.md 'Known gap'. This ticket closes it honestly: model those trees in design/frob.strata, or record reasoned exclusions -- never a silent scan-narrowing.