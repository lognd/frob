---
id: T-1023
title: 'INV burn-down: 50 invariant-anchor gaps (INV006 24 code claims, INV005 17
  unbound evidence, INV004/INV003 9 docs claims)'
state: done
kind: invariant
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/modules/
- invariants/
- src/frob/
- tests/unit/fleet/test_manifest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/fleet/test_manifest.py
  reason: 'INV006 burn-down anchored many invariants whose evidence lives in test

    files outside the declared docs/modules/, invariants/, src/frob/ scope

    globs (frob:tests directives point at pre-existing tests in tests/), and

    closing INV004/003 for docs/modules/fleet.md genuinely needed a NEW test

    (tests/unit/fleet/test_manifest.py) strengthening evidence for a real

    cross-module contract (manifest-dir-not-cwd resolution) that had no test

    proving the cwd-independence half of the claim before this ticket.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_relative_path_resolves_against_manifest_dir_not_cwd
- tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_flags_stale_generated_block
- tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires
- tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check THEN INV003-INV006 warnings are zero
  evidence:
  - tests/unit/fleet/test_manifest.py::TestLoadManifest::test_relative_path_resolves_against_manifest_dir_not_cwd
threat: null
component: null
---
Bind every normative claim to a checked invariant: INV006 code files with exclusivity claims need frob:invariant anchors; INV005 evidence must gain frob:tests edges to its anchor (dotted Class.method form only); INV003/INV004 docs claims need invariant markers. Write real property tests where an anchor has no evidence; do not water down claims to dodge the detector.