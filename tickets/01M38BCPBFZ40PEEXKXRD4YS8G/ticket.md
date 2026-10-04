+++
id = "01M38BCPBFZ40PEEXKXRD4YS8G"
title = "Document T-3047's review/decision node kinds in docs/strata/vmodel.md (blocked by T-3010 lease)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
parent = "01M0XNVQZ7V6VFKCBM4G9CR1C2"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:02:54Z"
aliases = ["T-6511"]
labels = ["v1-cluster:B3d"]
scope = ["docs/strata/vmodel.md"]
+++

found while working T-3047: KIND_REVIEW (requires commit+reason) and KIND_DECISION's new required reason attr are implemented and tested (strata-core/src/graph/vmodel/mod.rs) but docs/strata/vmodel.md was not updated -- held by T-3010's live scope lease throughout this ticket's work. Add a Node kinds entry for review, note decision now requires reason, once the lease frees.
