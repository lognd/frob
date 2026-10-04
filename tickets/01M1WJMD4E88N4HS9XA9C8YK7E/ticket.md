+++
id = "01M1WJMD4E88N4HS9XA9C8YK7E"
title = "deploy-script semantic checks: an image a script pulls must be one a job pushes; an unauthenticated smoke check must not assert against an admin-guarded route"
type = "task"
category = "triage"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4238"]
labels = ["milestone:1.1.0", "v1-cluster:B4"]
scope = ["src/frob/gates"]
+++

Consumer F-325/M2-4: two checks beyond existing pinning verification: (a) every image name a deploy script pulls is an image some job pushes (within-file string-set comparison); (b) a smoke-check URL must not name a route whose handler declares an admin/auth guard -- frob already resolves route symbols for guard-inventory purposes, so both halves of this contract violation are in its index. Not fixture-testable in frob's own tree: no deploy workflows or guarded routes exist here.
