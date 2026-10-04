+++
id = "01M44C4CEFHWYE7KNYV8QSHF9B"
title = "gob-testsupport: python probe fails on Windows runners (no python3 name); then require python tests there"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T21:11:46Z"
updated = "2026-10-04T23:20:56Z"
scope = ["crates/gob-testsupport/src/lib.rs", "crates/gob-dev/src/ci.rs"]

[[acceptance]]
text = "Given a host with only python, or only py -3, when python_test_prerequisites probes, then it resolves a Python 3 interpreter (python3, python, py -3 in that order)"
bound = true

[[acceptance]]
text = "Given a host with no Python 3 or no pytest, when FROB_REQUIRE_PYTHON_TESTS is unset, then the probe returns false (a named skip)"
bound = true
+++

found while working ~1CTNHZG: python_test_prerequisites probes python3, which a Windows runner lacks (python or py -3 instead). Accept those names, then drop the not-windows condition on FROB_REQUIRE_PYTHON_TESTS in crates/gob-dev/src/ci.rs steps().
