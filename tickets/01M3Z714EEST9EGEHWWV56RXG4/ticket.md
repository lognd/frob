+++
id = "01M3Z714EEST9EGEHWWV56RXG4"
title = "G14: grimble-capabilities: the matrix and CAP001-003"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:25Z"
updated = "2026-10-02T21:06:25Z"
idempotency_key = "m2-caps"
labels = ["milestone:2"]
scope = ["crates/grimble-capabilities/**", "crates/gob-ir/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z712KRPYF3DQG6ZFCWVPS7"

[[links]]
kind = "blocked-by"
target = "01M3Z71450ZE377RBK3EG1XSWC"

[[acceptance]]
text = "Given a node in a language with no detector for atom net, when the matrix is built, then the cell is unknown and the summary carries one Unresolved for the node"
bound = false
+++

grimble-model.md 9.6: cells uses, undeclared, declared-unused, excused, unknown, not-applicable; detector registry per atom and language; CAP001 undeclared Error, CAP002 declared-unused Warn, CAP003 unexcused Advisory for one release; unknown reported as Unresolved once per node.
