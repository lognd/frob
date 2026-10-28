+++
id = "01M1WJMD4X9V1J73F33REPG8H8"
title = "strata: connect a browser node's declared media/fetch capability grants to the CSP/edge policy that permits or denies them at runtime"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M1WJMD2PECRZNJSZ2ZEZ45SB"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-28T12:56:00Z"
aliases = ["T-4253"]
labels = ["v1-cluster:B3d", "triage:accepted", "no-story"]
scope = ["src/frob/strata"]
+++

Consumer F-386 item 2 (T-4182, shell round-5): a CSP is a string in an edge-server config snippet; frob check has no gate that reads it, and frob sys audit reasons about code capabilities (may fetch_url grants) not the edge policy that would permit or deny them at runtime -- nothing connects a browser node's declared media loads to the header that actually governs them. Not fixture-testable in frob's own tree: no CSP/edge-policy config exists here.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
