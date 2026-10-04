+++
id = "01M44J072TEWFTCB1AFVTN9C8B"
title = "Windows: pytest evidence reports backslash node ids and drops class names; then require python tests on Windows CI"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T22:54:21Z"
updated = "2026-10-04T23:33:24Z"
scope = ["crates/frob-evidence/src/provider.rs", "crates/gob-dev/src/ci.rs"]

[[acceptance]]
text = "Given a junit report whose testcase file attribute uses Windows backslash separators, when parse_junit builds node ids, then they are portable slash paths with the class segments kept (tests/test_probe.py::TestK::test_bad)"
bound = true

[[acceptance]]
text = "Given Windows CI with python and pytest installed, when FROB_REQUIRE_PYTHON_TESTS=1, then the pytest evidence and frob-tests pytest tests pass on Windows"
bound = true
+++

found while working ~8QSHF9B: with python and pytest present on nova-windows and FROB_REQUIRE_PYTHON_TESTS=1, 4 tests fail (frob-evidence a_pytest_node_id_runs_just_that_test, pytest_evidence_records_per_test_results_as_a_measured_record; frob-tests test_verb_runs_selected_pytest_tests_and_appends_pytest_evidence): executed/failed node ids come back as tests\test_probe.py::test_bad instead of tests/test_probe.py::TestK::test_bad. Normalise separators and class names from junit, then drop the not-windows condition on require_python in gob-dev ci.rs steps().
