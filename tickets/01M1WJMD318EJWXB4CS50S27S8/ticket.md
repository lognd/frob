+++
id = "01M1WJMD318EJWXB4CS50S27S8"
title = "playbook: a failure-injection repro test must assert every field of the response, not only the test-plan's named field"
type = "docs"
category = "todo"
priority = "low"
parent = "01M1T07P0DHR8Z9D3E3PRGDJ7B"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-09T20:42:00Z"
aliases = ["T-4193"]
labels = ["v1-cluster:F1", "triage:accepted"]
scope = ["docs/modules", "docs/design/testing.md"]
+++

Consumer F-307/H3-6 (T-4109): a process rule, not a code rule -- a test-plan row written as 'reports db and redis' was satisfied literally while a roll-up field stayed constant. Extends the prior audit's failing-dependency rule to cover every field of the response, not just the one named. Not fixture-testable as code; document the convention.
