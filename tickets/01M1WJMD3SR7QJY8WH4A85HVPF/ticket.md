+++
id = "01M1WJMD3SR7QJY8WH4A85HVPF"
title = "interface/adapter parity: every optional member of an invariant-marked port must be implemented by every adapter, or the adapter must declare the omission"
type = "task"
category = "triage"
priority = "low"
parent = "01M1WJMD1X14Z9P76XPX0QQ0NM"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:06:01Z"
aliases = ["T-4217"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates"]
+++

Consumer F-357/H4-5 (T-4157): optional interface methods make an incomplete implementation type-legal, so nothing at build or check time notices a fallback adapter implementing only 6 of 9 declared members. High-value generic mechanism, not domain-specific to the consumer's renderer. Fixture-testable: YES, frob's own Protocol/ABC-shaped ports with multiple implementations (e.g. gate registration interfaces) are a real fixture.
