---
id: T-1373
title: 'make coverage is red: nested coverage subprocess leak and the T-1333 CSafeLoader
  test'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_makefile_coverage.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
designated_repro_test: null
acceptance:
- text: GIVEN a full make coverage run WHEN the suite completes THEN tests/unit/test_makefile_coverage.py
    and tests/unit/test_ticket_store.py report no failures
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
  - tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
  - tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
threat: null
component: null
---
Found 2026-08-01 by the coordinator's full make coverage run, which the gates stage never exercises (frob check --only gates skips tests). Two distinct causes. (1) test_two_disjoint_sessions_combine_to_full_coverage and test_combine_then_xml_survives_a_stale_fixture_path spawn a nested 'coverage run' subprocess; under an outer make coverage the parent's COVERAGE_* environment leaks into the child and the nested run exits 1. The subprocess needs a coverage-clean env. (2) test_prefers_csafeloader_when_libyaml_present predates T-1333, which deliberately falls back to SafeLoader whenever a coverage tracer is active -- so the assertion is now false under coverage by design. The test must condition on the tracer the same way the fix does.