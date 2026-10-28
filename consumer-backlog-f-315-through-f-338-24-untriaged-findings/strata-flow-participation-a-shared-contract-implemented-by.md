+++
id = "01M1WJMD4TNBVD92RE7VRKXQ36"
title = "strata flow-participation: a shared contract implemented by more than one component must have both declare participation in one flow node"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-28T12:56:03Z"
aliases = ["T-4250"]
labels = ["v1-cluster:B3d", "triage:accepted", "no-story"]
scope = ["src/frob/strata"]
+++

Consumer F-327/M-6: two components each implement half of a single logical contract (an unauthenticated-redirect flow) with no cross-reference between their spec anchors, so they can diverge silently. Declare a strata flow node that both must declare participation in, so frob sys audit reports two participants implementing the same flow with divergent behaviour. Not fixture-testable in frob's own tree: no such multi-component flow-contract shape exists here.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
