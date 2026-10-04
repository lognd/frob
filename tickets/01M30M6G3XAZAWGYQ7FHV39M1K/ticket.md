+++
id = "01M30M6G3XAZAWGYQ7FHV39M1K"
title = "test_land_in_progress_window fixture drift: _refuse_if_land_in_progress_for_dispatch gained wait_timeout_s, test stub did not"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5245"]
scope = ["src/frob/app/ticket_runner/__init__.py", "tests/unit/test_land_in_progress_window.py"]
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_evidence_proceeds_while_only_land_lock_held and ::test_renumber_exits_while_only_land_lock_held both fail with TypeError: TestDispatchLayerWholeLandClassification._force_zero_wait.<locals>._zero_wait() got an unexpected keyword argument 'wait_timeout_s' at src/frob/app/ticket_runner/__init__.py:646. A recent change added a wait_timeout_s keyword argument to whatever _refuse_if_land_in_progress_for_dispatch calls at line 646, but this test file's own _force_zero_wait monkeypatch stub was not updated to accept it. Pure test-fixture drift (the production signature changed, the test double did not follow) -- fix by adding **kwargs or the explicit wait_timeout_s parameter to _force_zero_wait's inner _zero_wait.
