+++
id = "01M5F010QB00AR00D4HYVYYPWH"
title = "grimble-ci: CI001/CI006 grimble fallbacks and CI007, CI010"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-21T21:40:55Z"
scope = ["crates/grimble-ci/**", "docs/design/cicd.md", "changelog.d/01M5F010QB00AR00D4HYVYYPWH.added.md"]

[[acceptance]]
text = "CI001 flags external uses refs that are not a full commit SHA, skipping local, allowlisted and digest-pinned ones"
bound = false
+++

Deferred from ~8886VJ4: native fallbacks for the zizmor-bound pinned-ref and prt-head-checkout rules, plus CI007 and CI010.
