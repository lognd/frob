+++
id = "01M5FX89DV1WEPEB7831WBJZMR"
title = "gob-ir: engine::tests static_const_readonly... fails at HEAD"
type = "bug"
category = "todo"
priority = "medium"
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T18:58:21Z"
updated = "2026-10-21T18:58:21Z"
scope = ["crates/gob-ir/src/engine.rs"]
+++

found while working ~MVX4GEN: assertion !EngineVocab::default().has_external_writer(&base) at engine.rs fails on a clean tree too.
