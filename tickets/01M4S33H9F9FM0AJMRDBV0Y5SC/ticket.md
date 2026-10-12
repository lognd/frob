+++
id = "01M4S33H9F9FM0AJMRDBV0Y5SC"
title = "Fix base CI red: tool stage args in tests, message_origin in doctor snapshot"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-12T22:18:04Z"
updated = "2026-10-12T22:18:17Z"
scope = ["crates/frob-check/tests/tool_bind.rs", "crates/frob-obligations/tests/corpus.rs"]
+++

Three tests went stale after the tool-stage argv-template change (args now required) and the message_origin field landing.
