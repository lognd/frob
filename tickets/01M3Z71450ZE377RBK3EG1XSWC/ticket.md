+++
id = "01M3Z71450ZE377RBK3EG1XSWC"
title = "G11: grimble-bind: ownership and SYS001-005, SYS009-012"
type = "task"
category = "in-progress"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-03T01:07:02Z"
idempotency_key = "m2-bind"
labels = ["milestone:2"]
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**", "crates/grimble-check/**", "crates/gob-directives/**", "docs/reference/**", "docs/schemas/**", "crates/grimble/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712KRPYF3DQG6ZFCWVPS7"

[[links]]
kind = "blocked-by"
target = "01M3Z713RETBN30XBC6CK11FBF"

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[acceptance]]
text = "Given a node whose owns selector matches no unit, when grimble check runs, then SYS-UNRESOLVED fires with the selector text and status Unknown"
bound = false
+++

G02 semantics: build the binding relation from the four sources, ownership from selectors, SYS-UNRESOLVED and SYS-UNMODELED with opt-in modeled selectors, the F0/F1 Unresolved behaviour.
