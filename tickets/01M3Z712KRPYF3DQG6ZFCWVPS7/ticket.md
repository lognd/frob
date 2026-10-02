+++
id = "01M3Z712KRPYF3DQG6ZFCWVPS7"
title = "G02: binding semantics over U"
type = "docs"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:44:43Z"
idempotency_key = "m2-binding"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712GP8XV2WEAS1VHQ7FD4"

[[acceptance]]
text = "Given each v1 strata binding mechanism, when looked up in the document, then it maps to exactly one of the four sources with a status"
bound = false
+++

grimble-model.md 9.1: define the relation B between model entities and U identities with Must/May/Unknown from the four ranked sources (grimble:binds directives, owns selectors, pack inference, nothing); precedence and conflict rules; how SCIP occurrences enter; what each of the twelve v1 mechanisms becomes; the drift rules SYS001-012 restated as predicates over B and the facets, each with polarity and its Unresolved conditions.
