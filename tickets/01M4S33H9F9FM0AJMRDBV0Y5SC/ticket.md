+++
id = "01M4S33H9F9FM0AJMRDBV0Y5SC"
title = "Fix base CI red: tool stage args in tests, message_origin in doctor snapshot"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-12T22:18:04Z"
updated = "2026-10-13T03:20:47Z"
scope = ["crates/frob-check/tests/tool_bind.rs", "crates/frob-obligations/tests/corpus.rs", "docs/design/boundaries.md"]

[[acceptance]]
text = "Given the stale tool_bind test, when it runs, then it passes"
bound = true

[[acceptance]]
text = "Given the exc017 corpus, when mdtest_corpus runs, then it passes"
bound = true

[[acceptance]]
text = "Given frob-mirror, when the layering test runs, then it passes"
bound = true
+++

Three tests went stale after the tool-stage argv-template change (args now required) and the message_origin field landing.
