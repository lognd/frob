+++
id = "01M5FX89B11DR9HP9QH19GKAYY"
title = "unity pack: feed csharp_dynamic_calls into reach and obligations"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T18:58:21Z"
updated = "2026-10-21T20:21:53Z"
scope = ["crates/frob-tests/src/reach.rs", "crates/frob-obligations/src/cov.rs", "crates/frob-obligations/tests/unity_dynamic.rs", "docs/design/dotnet-unity.md", "changelog.d/01M5FX89B11DR9HP9QH19GKAYY.changed.md"]

[[acceptance]]
text = "An enabled unity pack makes an unresolved COV001 report name the dynamic-call reason"
bound = false

[[acceptance]]
text = "A disabled or gated-out pack leaves the unresolved report anonymous"
bound = false
+++

found while working ~MVX4GEN: csharp_dynamic_calls (gob-symbols) has no non-test consumer; frob-tests reach.rs and frob-obligations unity.rs should call it with the pack EngineVocab to report the named reason.
