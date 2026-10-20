+++
id = "01M3Z8NVCBM9KXN5ZY97QWX8P1"
title = "gob-ir: make printer, symref pass and from_term stack-safe"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:35:12Z"
updated = "2026-10-03T02:43:02Z"
idempotency_key = "m2-ir-stack"
labels = ["milestone:2"]
scope = ["crates/gob-ir/**"]

[[acceptance]]
text = "Given a term nested one million levels deep, when printed, digested and its symrefs computed, then no stack overflow occurs and the results are deterministic"
bound = true
+++

Found by 01M3Z712DPZN71ZQDS6PXY6QQV: the printer, the symref pass and from_term recurse over term depth, so a deep term (generated code, long expression chains) can overflow the stack, which breaks Theorem 1's totality claim in practice. Convert to explicit work stacks; add a test with a 1e6-deep term; memoize scope resolution per reference.
