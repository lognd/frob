---
id: T-1442
title: T-1420 delivered portion 2
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: T-1420
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_threat_models.py
- src/frob/strata/_threat_catalog_benign.py
- src/frob/strata/_threat_catalog_cwe.py
- src/frob/strata/_threat_catalog_quality.py
- src/frob/strata/_threat_discharge.py
- tests/unit/strata/test_threat.py
- tests/unit/strata/test_litmus_cwe.py
- tests/unit/strata/test_managed.py
- tests/unit/strata/test_store_code_may.py
- tests/unit/strata/test_sysdoc.py
- tests/unit/strata/test_audit.py
- tests/test_gates.py
- docs/guides/extending/benign-capabilities.md
- docs/guides/extending/threat-catalog.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_litmus_cwe.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_managed.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_store_code_may.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_sysdoc.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_gates.py
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/extending/benign-capabilities.md
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/extending/threat-catalog.md
  reason: test/doc files whose frob:tests/frob:describes edges were repointed in the
    same land
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/strata/test_threat.py::TestDischargeCompleteness::test_fired_obligation_discharged_by_proved_claim
- tests/unit/strata/test_threat.py::TestBenignCapability::test_empty_reason_is_rejected
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_reuses_the_exec_capability_join
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_quality_catalog_never_leaks_into_owasp_top_10_view
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_with_same_shape_discharges
- tests/unit/strata/test_store_code_may.py::TestStoreMayFeedsThreat003::test_store_with_exec_may_fires_undischarged_cwe_94
- tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
designated_repro_test: null
threat: null
component: null
---
Continuation of T-1420's LARGE001 burndown (parent ticket, precedent:
T-1441 landed the first delivered portion). This portion splits
src/frob/strata/_threat.py (2522 lines, the largest remaining Python
file on T-1420's list after T-1441) into five modules along its own
existing seams:

- src/frob/strata/_threat_models.py: WeaknessEntry/OutOfScopeEntry/
  BenignCapability/ThreatViolation/ThreatReport (the record shapes
  everything else builds from)
- src/frob/strata/_threat_catalog_benign.py: DEFAULT_BENIGN_CAPABILITIES
- src/frob/strata/_threat_catalog_cwe.py: CWE_CATALOG/CWE_TOP_25_CATALOG/
  VIEWS/CWE_TOP_25_VIEWS family
- src/frob/strata/_threat_catalog_quality.py: QUALITY_CATALOG/
  ALL_CATALOG/QUALITY_OUT_OF_SCOPE/QUALITY_VIEWS family
- src/frob/strata/_threat_discharge.py: the THREAT003 mitigation-
  chokepoint verification family (_mitigation_is_chokepoint and every
  helper check_discharge_completeness needs) -- a single cohesive
  concern per the module's own Phase C docstring

All five new files land under 800 lines; _threat.py itself dropped from
2522 to 757 lines. _threat.py re-exports every moved name so every
existing `from frob.strata._threat import X` caller (production and
test) keeps working unchanged; tests/production code that imported
moved PRIVATE helpers directly are repointed to their new module.
frob:tests directives and frob:describes doc anchors (docs/guides/
extending/benign-capabilities.md, docs/guides/extending/threat-
catalog.md) that named the old _threat.py location for moved symbols
are repointed in the same change (DRIFT002 caught these before the fix,
confirming the check exercises the edges).

Verification (foreground, timeout-wrapped, per playbook section 3b):
- pytest on every touched/covering test file: tests/unit/strata/
  test_threat.py, test_litmus_cwe.py, test_managed.py,
  test_store_code_may.py, test_sysdoc.py, test_audit.py, plus
  tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes --
  all green.
- `frob check --only archgate --only wire --only dead_symbols --only
  drift --only doclink --only fmt`: 0 errors (49 LARGE001 warnings, down
  from 50 before this land; 1 pre-existing waiver unaffected). WIRE001
  did NOT fire on any of the five relocated symbol groups -- T-1431's
  relocation-awareness held.
- ruff check / ruff format --check clean on every touched/new file.

LARGE001 count: 50 -> 49. _threat.py itself (757 lines) drops off the
list entirely (under the 800 threshold); no new file crosses it. Net:
-1 file on T-1420's remaining list.