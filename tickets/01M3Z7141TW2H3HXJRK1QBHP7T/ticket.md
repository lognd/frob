+++
id = "01M3Z7141TW2H3HXJRK1QBHP7T"
title = "G10: grimble-arch: CYCLE, LARGE, DEAD"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:24Z"
updated = "2026-10-02T21:06:24Z"
idempotency_key = "m2-arch"
labels = ["milestone:2"]
scope = ["crates/grimble-arch/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713YNM5666B7YFEHPFVKD"

[[acceptance]]
text = "Given two crates importing each other, when grimble check runs, then CYCLE names both"
bound = false

[[acceptance]]
text = "Given a private fn reachable only through a May edge, when DEAD evaluates, then it reports Unresolved, not dead"
bound = false
+++

The first model-free findings over the U graph: import cycles (CYCLE), oversized units by a knob (LARGE), unreferenced non-public units (DEAD with May edges respected: Unresolved when any Unknown edge could reach the unit).
