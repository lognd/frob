+++
id = "01M406C57V9ECX2YEKFZ5P8YK3"
title = "releases.md: close the ten gaps found by the 0.532.0 planner"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T06:14:12Z"
updated = "2026-10-03T15:28:26Z"
idempotency_key = "m2-releases-gaps"
labels = ["milestone:2", "area:release"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given releases.md, monorepo.md 4 and pm-enforcement.md 7, when read, then each of the ten gaps is specified and no rule id is defined twice"
bound = false
+++

Object storage for milestones and cycles, lockstep tag scheme versus monorepo.md 4, PM014 number conflict, forecast in release status, what the wheel bundles, tag trigger versus the publish gate, the v1 CHANGELOG.md and the dev channel branch, owner actions for registry tokens, CI status source, and the dangling section-7 references.
