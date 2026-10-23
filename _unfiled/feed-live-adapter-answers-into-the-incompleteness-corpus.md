+++
id = "01M5HGCQ5CDB7HEEFGTRVP9DA6"
title = "Feed live adapter answers into the incompleteness corpus observed column"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T09:52:03Z"
updated = "2026-10-23T05:15:15Z"
scope = ["crates/gob-check/**", "crates/gob-testsupport/**"]

[[acceptance]]
text = "a test runs the real adapters over the incompleteness oracle corpus and produces the observed answers"
bound = false

[[acceptance]]
text = "the test fails when the committed observed column differs from the live adapter answers"
bound = false
+++

Found while working ~6SJ9WYR: the committed oracle corpus records observed answers by hand; run the real adapters to produce them in CI.
