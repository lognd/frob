+++
id = "01M40PAJ47VC22S2EXC3A9XXRK"
title = "pm-enforcement.md: align knob defaults with releases.md and the landed [pm] tables"
type = "docs"
category = "in-progress"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T10:52:57Z"
updated = "2026-10-03T10:52:57Z"
idempotency_key = "m2-pm-doc-defaults"
labels = ["milestone:2"]
scope = ["docs/design/pm-enforcement.md"]

[[acceptance]]
text = "Given pm-enforcement.md and releases.md, when read, then the WIP and history defaults agree with the landed config"
bound = false
+++

Found on ~H83JZSW: pm-enforcement.md 6 says [pm.wip] in_progress_per_identity defaults to 0 (off) while releases.md 2 (D83, newer) says 1; the landed tables use 1, in_progress 2 and min_history 3 (no doc gave min_history a default). Make pm-enforcement.md agree and point to releases.md 2 as the policy source.
