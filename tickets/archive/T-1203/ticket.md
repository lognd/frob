---
id: T-1203
title: 'strata: may-mutation audit -- prove every may is load-bearing and double-detected'
state: done
kind: invariant
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/gates/_sys.py
- tests/unit/strata/**
- tests/golden/**
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
- tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable
designated_repro_test: null
acceptance:
- text: GIVEN any single may declaration in any loaded .strata model WHEN it is deleted
    in a mutated copy THEN self-conformance yields at least one SYS100 AND the seccomp/export
    golden diff yields a second, independent finding -- two errors from two mechanisms
    with no shared blind spot
  evidence:
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
  - tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable
- text: GIVEN any single may declaration WHEN it is substituted for a different capability
    kind THEN the mutated copy yields the SYS100 plus SYS101 pair
  evidence:
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
  - tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable
- text: GIVEN the harness runs THEN it also asserts baseline SYS101 count is zero
    (every may proven load-bearing, no silently-deletable declarations) and that no
    existing waiver masks a mutation finding (mutation run evaluated with waivers
    disabled or each masked mutation reported)
  evidence:
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
  - tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable
- text: GIVEN a capability kind the effect scanner cannot observe THEN the harness
    fails closed naming the undetectable kind rather than skipping it -- scanner blind
    spots become findings, not silence
  evidence:
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
  - tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable
threat: null
component: null
---
User directive 2026-07-29: ensure changing any may in the .strata files produces two errors. Today SYS100 (observed-undeclared) and SYS101 (declared-unobserved) cover the two directions but a pure deletion yields one finding, and the guarantee rests on three unproven assumptions: baseline SYS101=0, scanner detection completeness per capability kind, and no waiver masking (e.g. a SYS100:fs-write waiver would swallow the mutation). No mutation harness exists over design/frob.strata -- tests/unit/strata/test_conform_eval_needle.py is a fixture false-positive regression, not detection-completeness proof. Design: a litmus-style mutation-audit (frob sys mutation-audit or a hypothesis-parametrized test) that for EVERY may in every loaded model checks a mutated in-memory copy (delete -> >=1 SYS100; substitute -> SYS100+SYS101 pair), plus an independent second layer via the _export.py seccomp allowlist golden (tests/golden/frob_export_k8s.yaml precedent) so semantic and artifact detectors cannot share a blind spot. Interacts with T-1196 (multi-file split: harness must iterate every loaded file) and the fs.read/fs.write migration landing this drive -- build atop the migrated spellings.