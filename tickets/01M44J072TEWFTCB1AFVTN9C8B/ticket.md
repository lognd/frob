+++
id = "01M44J072TEWFTCB1AFVTN9C8B"
title = "Windows: pytest evidence reports backslash node ids and drops class names; then require python tests on Windows CI"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T22:54:21Z"
updated = "2026-10-04T22:54:21Z"
scope = ["crates/frob-evidence/src/provider.rs", "crates/gob-dev/src/ci.rs"]
+++

found while working ~8QSHF9B: with python and pytest present on nova-windows and FROB_REQUIRE_PYTHON_TESTS=1, 4 tests fail (frob-evidence a_pytest_node_id_runs_just_that_test, pytest_evidence_records_per_test_results_as_a_measured_record; frob-tests test_verb_runs_selected_pytest_tests_and_appends_pytest_evidence): executed/failed node ids come back as tests\test_probe.py::test_bad instead of tests/test_probe.py::TestK::test_bad. Normalise separators and class names from junit, then drop the not-windows condition on require_python in gob-dev ci.rs steps().
