+++
id = "01M3Z714MQBXMW4PJVRQNDWNDM"
title = "G16: kernel port: CLAIM and VMOD families"
type = "task"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-19T13:04:17Z"
idempotency_key = "m2-kernel"
labels = ["milestone:2"]
scope = ["crates/grimble-kernel/**", "crates/grimble-model/**", "docs/design/grmb-spec.md", "docs/reference/rules/CLAIM003.md"]

[[links]]
kind = "blocked-by"
target = "01M3Z712KRPYF3DQG6ZFCWVPS7"

[[links]]
kind = "blocked-by"
target = "01M3Z713VGKF4Z0JJ3263XJMC3"

[[acceptance]]
text = "Given a claim bound to a unit with no evidence, when grimble check runs, then CLAIM reports Unresolved, never satisfied"
bound = true
+++

notes/v1/strata.md kernel semantics over U: claims checked against bindings and evidence, V-model links between requirement, design and verification entities, both with polarity and Unresolved conditions.
