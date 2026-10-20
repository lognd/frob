+++
id = "01M3ZYQ4T92J0GKZFBG5MAFAAY"
title = "Release track: scrumban flow wired to milestones, cycles and incremental releases (D83)"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T04:00:23Z"
updated = "2026-10-03T04:05:29Z"
idempotency_key = "m2-release-track-design"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given releases.md, when read, then milestones, cycles, the scrumban policies, the readiness gate, the cut, channels, the version scheme and the v2 milestone list are specified and tied to existing PM rules"
bound = false
+++

Owner request 2026-10-03: set up milestones for a release track and keep to scrumban principles; the sprint-planning practices already designed (pm-enforcement.md 4-6: cycles, capacity, velocity, forecasts, flow metrics, WIP limits, PM rules) must be wired into an incremental build and release system. v1 frob ships an alpha on PyPI (0.531.0) with no guarantees. Write docs/design/releases.md: milestone = version, cycle = time box (v1 T-5133 lesson), scrumban pull with WIP limits and a replenishment order point, release readiness and cut verbs, channels (dev, alpha, stable), version scheme versus the existing PyPI line, the v1 release-workflow lessons (manylinux 2_28, macOS cross build, artifact smoke, release concurrency), and the v2 milestone list mapping existing epics to releases.
