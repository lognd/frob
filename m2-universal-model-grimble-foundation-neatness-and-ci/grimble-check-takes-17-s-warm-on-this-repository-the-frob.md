+++
id = "01M403Q1W4PMWRM8GXPRS10WX7"
title = "grimble check takes 17 s warm on this repository; the frob sibling stage dominates check time"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:27:43Z"
updated = "2026-10-03T05:41:17Z"
idempotency_key = "m2-grimble-warm-17s"
labels = ["milestone:2", "perf"]
scope = ["crates/grimble/**", "crates/grimble-check/**", "crates/grimble-bind/**", "crates/grimble-model/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given a release build and a warm cache on this repository, when grimble check runs, then it finishes under 1 s"
bound = true

[[acceptance]]
text = "Given a release build and a warm cache, when frob check runs, then the budgeted stages plus the sibling stage finish under 2 s"
bound = true
+++

Measured 2026-10-03 with debug binaries: frob check warm 20 s, of which sibling:grimble 17.1 s (frob's own budgeted stages 2.8 s: graph 1.5 s, directives 1.0 s); grimble check alone 16.7 s, 513 MB peak, although .grimble/cache.sqlite exists. Measure release builds first (the 2 s warm budget is for release); then profile (cargo flamegraph or perf, samply) the warm grimble path, find what is recomputed on every run, and make the warm path hit its cache (per-file payloads, the model load, binding, the sibling document). Also report frob's graph and directives stages warm in release. Target: grimble warm under 1 s and frob check warm under the 2 s budget in release on this repository.
