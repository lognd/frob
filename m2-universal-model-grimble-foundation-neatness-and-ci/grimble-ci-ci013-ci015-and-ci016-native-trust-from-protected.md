+++
id = "01M5F010V5GV0B7KJ7M5QQG70Q"
title = "grimble-ci: CI013-CI015 and CI016 (native, trust-from-protected-ref)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-23T08:15:20Z"
scope = ["crates/grimble-ci/**", "docs/reference/rules/**", "docs/schemas/**", "docs/design/cicd.md", "Cargo.lock"]

[[acceptance]]
text = "CI013, CI014 and CI015 are declared in grimble-ci delegating to actionlint/zizmor findings, each with a fire and a no-fire test"
bound = false

[[acceptance]]
text = "CI016 (trust from protected ref) is a native rule with fire, no-fire and unresolved tests"
bound = false
+++

Deferred from ~8886VJ4: the actionlint/zizmor-delegated rules CI013-CI015 and native CI016.
