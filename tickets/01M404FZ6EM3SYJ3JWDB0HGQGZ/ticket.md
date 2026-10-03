+++
id = "01M404FZ6EM3SYJ3JWDB0HGQGZ"
title = "Document the grimble binding cache in rules.md (warm path)"
type = "docs"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:41:20Z"
updated = "2026-10-03T05:41:20Z"
idempotency_key = "m2-doc-binding-cache"
labels = ["milestone:2", "good-first"]
scope = ["docs/design/rules.md"]

[[acceptance]]
text = "Given rules.md, when read, then the binding cache key and scope are described"
bound = false
+++

Follow-up of ~RS10WX7. ## Start here
Read crates/grimble-check/src/bind_cache.rs and docs/design/rules.md (caching and warm runs). Add a short paragraph: grimble check caches the binding summary (rows of B as document items, SYS findings, subject counts) keyed by every walked file's path and content digest, the grimble.lock bytes and the [grimble] knobs, scoped by the engine fingerprint; grimble ack still builds the full binding. Test: frob check --ticket passes. Ask the coordinator if unsure.
