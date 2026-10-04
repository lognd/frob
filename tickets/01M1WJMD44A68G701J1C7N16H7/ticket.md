+++
id = "01M1WJMD44A68G701J1C7N16H7"
title = "coverage-over-a-registry is not coverage-over-the-real-surface: add a surface-enumeration check alongside registry-totality tests"
type = "task"
category = "triage"
priority = "medium"
parent = "01M1WJMD2FWKPS1J7MPF18KDVY"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4228"]
labels = ["milestone:1.1.0", "v1-cluster:B4"]
scope = ["src/frob/gates"]
+++

Consumer F-373/P4 (T-4175): a totality test proves every registered error-set member has an HTTP mapping -- a claim about the registry, not about the response surface. Nothing enumerates the error responses the framework itself can actually produce. Rule: fire one deliberately malformed request at each real route in the app's route table and assert the envelope, alongside the registry-totality test. Same shape as frob's own risk (a gate registered in one list and absent from another) named across this session's own drives. Not fixture-testable in frob's own tree: no HTTP route table exists here.
