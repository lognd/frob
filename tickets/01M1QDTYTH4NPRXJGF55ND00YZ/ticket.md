+++
id = "01M1QDTYTH4NPRXJGF55ND00YZ"
title = "add a jest test collector (frob.testing._collect_ts currently vitest-only)"
type = "task"
category = "triage"
priority = "low"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-04T21:06:23Z"
aliases = ["T-3921"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/testing/_collect_ts.py"]
+++

Found while working T-3847 (evidence verification bucket wiring). frob.testing.collect_ts_tests only recognizes vitest (_package_json_uses_vitest gates it); jest is a distinct JS/TS test runner with its own CLI invocation, JSON reporter shape, and test-id spelling -- collecting it is genuine new collector work, not a generalization of the existing vitest path, so it is out of T-3847's bug-fix scope. Decide jest's node-id shape (jest --listTests / --json reporter) and either extend _collect_ts.py to dispatch on which runner a package.json declares, or add a sibling collect_jest_tests + LANGUAGE_COLLECTORS entry (frob.testing._collect.LANGUAGE_COLLECTORS, T-3847).
