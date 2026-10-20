+++
id = "01M0XNVQZ7V6VFKCBM4G9CR1C2"
title = "Type-checked code review and decision records: review as a graph node with provenance, decisions carrying their reason as data"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M0XNVQXWNFXBK2AGM3QF2P3A"
reporter = "human"
created = "2026-08-26T00:00:00Z"
updated = "2026-08-26T00:00:02Z"
aliases = ["T-3047"]
labels = ["milestone:0.535.0"]
scope = ["strata-core/src/graph/model.rs", "strata-core/src/graph/vmodel/mod.rs", "tests/unit/strata/test_vmodel_review_decision.py", "tests/unit/strata/test_vmodel_check.py"]
+++

## Unblock log
- 2026-09-23: unblocked by T-5460 -- L0 dropped: edge kinds already landed (T-3007/T-3042)
- 2026-09-24: unblocked by T-3010 -- coordinator directive 2026-09-24: T-3010's own blocked_by edge is sequencing-only (shared graph schema file); building T-3047 on top of t-3010 branch content merged in, diffs kept separable, T-3010 lands independently via its own land
