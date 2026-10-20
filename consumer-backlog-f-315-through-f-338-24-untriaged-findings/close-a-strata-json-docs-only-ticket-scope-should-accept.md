+++
id = "01M1WJMD3AG02SRQRKBNA75GVF"
title = "close: a strata/json/docs-only ticket scope should accept bound test or cmd evidence without a touched Python symbol"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:02:14Z"
aliases = ["T-4202"]
labels = ["milestone:1.1.0", "v1-cluster:B3d"]
scope = ["src/frob/tickets"]
+++

Consumer F-336 (T-4135). A ticket whose scope is entirely non-code (a .strata file, a ratchet lock json) cannot close: EvidenceScopeUnbound fires because no touched/scope Python symbol exists, even with a genuinely bound test as evidence. Adjacent to T-4170's family (evidence rules assuming a code-symbol shape) but a distinct trigger -- non-code scope, not out-of-scope test file. Fixture-testable: YES.
