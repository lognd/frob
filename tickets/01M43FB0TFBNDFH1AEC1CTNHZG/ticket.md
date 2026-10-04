+++
id = "01M43FB0TFBNDFH1AEC1CTNHZG"
title = "CI: install pytest and set FROB_REQUIRE_PYTHON_TESTS so pytest-backed tests cannot skip"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T12:48:35Z"
updated = "2026-10-04T20:51:54Z"
scope = [".github/workflows/ci.yml"]
+++

found while working ~M525Y1M: the pytest-running tests skip with a named reason when python3 or pytest is absent; CI should install pytest and set FROB_REQUIRE_PYTHON_TESTS=1 so a missing tool fails instead of skipping.
