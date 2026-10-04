+++
id = "01M1WJMD4SVXKVMQSBEMTHZXYJ"
title = "client-side totality mirror: export a server registry's total code/field set and require the consumer to enumerate and handle/ignore every entry"
type = "task"
category = "triage"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4249"]
labels = ["milestone:1.1.0", "v1-cluster:B4"]
scope = ["src/frob/gates"]

[[links]]
kind = "blocked-by"
target = "01M1T07NZ8409YTCHE1KFNZ4W8"
+++

Consumer F-327/M-1,M-5 (T-4135 sub-epic, API contract audit), consolidated with F-362/M4-5 (T-4166 -- splitting a display-only error-code list from a needs-recovery axis is the client-side half of this same totality gap). A backend's _assert_total_coverage()-style check proves every registered error has a mapping -- a claim about the registry, not the response surface as seen by the client. Nothing enumerates the codes the backend can emit and requires the consumer to enumerate and handle/ignore each. Blocked by T-4072 (generated-types staleness + hand-written-interface ban): this needs the generated contract artifact T-4072 establishes to exist before a client-side totality test can be written against it. Not fixture-testable in frob's own tree: no client/server duo exists here.
