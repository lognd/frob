---
id: T-1091
title: 'strata: drop SYS103''s _PACKAGE_ROOT restriction now that the self-model covers
  tests/scripts/native trees (T-1079 follow-up)'
state: done
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_selfconform.py
- docs/modules/strata.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/strata.md
  reason: AFFECT001 names docs/modules/strata.md#sys-cov-coverage-totality-sys103-t-0667
    as _coverage_totality_scan_prefix's affects()-closure doc; the T-1079 follow-up
    section there needs a T-1091 update recording the restriction was actually dropped,
    mirroring the T-1113 doc-scope precedent
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_fires_outside_src_frob_layout
designated_repro_test: null
threat: null
component: null
---
T-1079 modeled tests/**, scripts/**, frob-core/src/**, strata-core/src/**
in design/frob.strata (testsuite, scripts_ops, strata_core_native,
frob_core_native nodes) so an unrestricted SYS103 scan against the model
now returns zero findings. `_coverage_totality_scan_prefix`
(src/frob/strata/_selfconform.py) itself was out of T-1079's declared
scope and still restricts the LIVE SELFAUDIT001 gate to _PACKAGE_ROOT
("src/frob") on frob's own tree -- now that the model covers the whole
repo with zero findings either way, that restriction can be dropped (or
narrowed to a real, disclosed exception) so the live gate actually
checks what the model now claims to cover, closing the gap for real
rather than just in a test harness.