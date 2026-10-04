+++
id = "01M1WJMD3YVXB4TJK141S8ACP0"
title = "strata: mark outbound fetch capabilities volatility=external; a volatility=external source may not ground a build-failing equality check"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD26NR9SKQCEFEHS7ENJ"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4222"]
labels = ["v1-cluster:B3d", "triage:accepted"]
scope = ["src/frob/strata"]
+++

Consolidates F-362/H4-2 (T-4166: a build node's grant to fetch third-party data carries no attribute saying that data is volatile, so nothing objects to comparing it for byte equality against a committed file) with F-386 item 7 (T-4182: the same gate restated, plus a note that a hand-picked field allowlist was implemented instead of a volatility classification, which is why the field partition is a judgement call rather than a structural fix). Not fixture-testable in frob's own tree: no external-fetch-grounding-a-build-oracle pattern exists here.
