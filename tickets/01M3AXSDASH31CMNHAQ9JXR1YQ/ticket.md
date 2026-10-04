+++
id = "01M3AXSDASH31CMNHAQ9JXR1YQ"
title = "resilience gaps not in REL (SYSDESIGN301+)"
type = "story"
category = "triage"
priority = "low"
parent = "01M3AXSDACKS00T3E853M1J0DR"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:42Z"
aliases = ["T-6489"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: resilience gaps not in REL (SYSDESIGN301+)
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

Per SYSDESIGN-INVENTORY.md's REL-family conclusion ("health/timeout/retry/backoff/circuit-
breaker/bulkhead is EXHAUSTIVELY COVERED"), this story files only what REL genuinely does not
cover: deadline propagation across hops (distinct from REL200/201's per-hop timeout, PARTIAL
per the inventory), a server-wide/process retry budget (distinct from REL220's per-flow
backoff/jitter), request hedging (new grammar from Story A), and cache stampede-guard
declaration (new grammar from Story A). Idempotency-key-on-unsafe-retries is already COVERED
by REL221 and is not re-filed here.
