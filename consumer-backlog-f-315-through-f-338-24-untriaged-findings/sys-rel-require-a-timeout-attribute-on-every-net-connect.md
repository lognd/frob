+++
id = "01M1WJMD4NCQE6YN00KZHB0RTE"
title = "SYS/REL: require a timeout attribute on every net.connect/fetch_url strata grant, and flag a grant that declares none"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-28T12:56:07Z"
aliases = ["T-4245"]
labels = ["v1-cluster:B3d", "triage:accepted", "no-story"]
scope = ["src/frob/strata"]
+++

Consumer F-326/M2-1: strata has vocabulary for a component's own explicit timeout obligation, but a bare may net.connect via <file> grant carries no obligation of its own, so a capability can be added with no timeout at all. A one-line model change with repo-wide reach. Fixture-testable: YES if frob's own design/frob.strata carries net.connect-shaped grants; otherwise partial.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
