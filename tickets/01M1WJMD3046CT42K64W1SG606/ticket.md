+++
id = "01M1WJMD3046CT42K64W1SG606"
title = "route-inventory check: a handler returning a dict/mapping literal response must declare a response model"
type = "task"
category = "todo"
priority = "low"
parent = "01M1T07P0DHR8Z9D3E3PRGDJ7B"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:22Z"
aliases = ["T-4192"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates"]
+++

Consumer F-307/H3-7 (T-4109): COV/WIRE see the response type as referenced because some routes use it, masking routes returning a bare dict literal instead. Same family as the existing SIT-011 guard-inventory pattern. Not fixture-testable in frob's own tree: no HTTP routes exist here. Consumer-blocking: latent for us.
