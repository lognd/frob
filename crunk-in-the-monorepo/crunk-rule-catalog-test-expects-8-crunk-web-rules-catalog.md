+++
id = "01M5F5H31HMHWAF2SPVK4WQ2S3"
title = "crunk rule_catalog test expects 8 crunk-web rules, catalog has 15"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-21T12:03:43Z"
updated = "2026-10-21T12:50:23Z"
scope = ["crates/crunk/tests/rule_catalog.rs"]

[[acceptance]]
text = "the rule_catalog test asserts the real crunk-web rule count and passes"
bound = true
+++

crates/crunk/tests/rule_catalog.rs asserts 8 pack rules; crunk-web now ships 15 (WEBPERF101-105 etc). Found while working ~4KW24RJ; pre-existing, unrelated.
