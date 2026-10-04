+++
id = "01M44C4CEFHWYE7KNYV8QSHF9B"
title = "gob-testsupport: python probe fails on Windows runners (no python3 name); then require python tests there"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T21:11:46Z"
updated = "2026-10-04T22:26:51Z"
scope = ["crates/gob-testsupport/src/lib.rs", "crates/gob-dev/src/ci.rs"]
+++

found while working ~1CTNHZG: python_test_prerequisites probes python3, which a Windows runner lacks (python or py -3 instead). Accept those names, then drop the not-windows condition on FROB_REQUIRE_PYTHON_TESTS in crates/gob-dev/src/ci.rs steps().
