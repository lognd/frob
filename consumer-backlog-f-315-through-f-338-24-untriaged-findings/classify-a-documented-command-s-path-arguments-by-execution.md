+++
id = "01M1WJMD4DGES2VA3SZVXKMGDY"
title = "classify a documented command's path arguments by execution context (container namespace vs host) against declared mounts"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-28T12:56:03Z"
aliases = ["T-4237"]
labels = ["v1-cluster:B4", "triage:accepted", "no-story"]
scope = ["src/frob/gates"]
+++

Consumer F-325/M2-1: a bound test checks a runbook's structure and file/service existence but cannot distinguish 'this path exists in the repo' from 'this path exists in the namespace the command runs in'. Cheap bounded version: flag any host-side path under a mount point compose declares as a named volume. Not fixture-testable in frob's own tree: no containers/compose files exist here.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
