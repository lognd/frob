+++
id = "01M76JWX3J0FAVBXRSVNH34WZN"
title = "Windows nextest: frob-check corpus mdtest_corpus exceeds the 120 s timeout"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-12T00:35:36Z"
updated = "2026-11-12T17:32:11Z"
idempotency_key = "win-mdtest-timeout"
labels = ["good-first", "no-story"]
scope = [".config/nextest.toml", "changelog.d/**"]

[[acceptance]]
text = "nextest ci profile gives frob-check mdtest_corpus a reviewed 300 s slow-timeout override with a reason, following the gob-check ui_product precedent"
bound = true
+++
