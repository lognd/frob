+++
id = "01M0XNVQZW9RSAYB7M8S8FXM30"
title = "TDD commit protocol: test-first commit marks the test xfail(strict=True), implementation commit removes it; a surviving xfail is tracked debt"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M0XNVQXWNFXBK2AGM3QF2P3A"
reporter = "human"
created = "2026-08-26T00:00:00Z"
updated = "2026-10-09T20:41:49Z"
aliases = ["T-3068"]
labels = ["v1-cluster:C4b", "triage:accepted"]
scope = ["src/frob/gates/_tdd_order.py", "tests/gates/test_tdd_order.py", "docs/modules/gates.md", "docs/design/rules.md"]
+++

## Unblock log
- 2026-09-24: unblocked by T-3067 -- coordinator directive 2026-09-24: build on top of branch t-3067 merged in, diffs kept separable; T-3067 already queued, its own land is independent
