+++
id = "01M6BNZXEFBGVYDGB19VK378CC"
title = "Add build_id knob to fake_sibling and an end-to-end build-mismatch test"
type = "task"
category = "in-progress"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T13:50:10Z"
updated = "2026-11-01T17:16:50Z"
scope = ["crates/gob-testsupport/src/bin/fake_sibling.rs", "crates/frob-check/tests/it/sibling.rs"]

[[acceptance]]
text = "fake_sibling reports a configurable build_id; integration test covers build_mismatch_warning"
bound = true
+++
