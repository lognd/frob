+++
id = "01M43ARXVD5PXP6ZBVFC2F4ZMQ"
title = "gob-symbols: bounded constant evaluation of TS literals"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-06T04:31:33Z"
idempotency_key = "crunk-plan-tsconst"
labels = ["area:crunk"]
scope = ["crates/gob-symbols/src/typescript/consteval.rs", "crates/gob-symbols/tests/typescript_consteval.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[acceptance]]
text = "Given `const gap = 8; style={{ margin: gap }}` in another file via import, when evaluated, then the value 8 is resolved with its origin span"
bound = false

[[acceptance]]
text = "Given a cyclic or over-budget evaluation, when run, then the result is Unresolved with the reason"
bound = false

[[acceptance]]
text = "Given the Python consteval vectors, when run, then every resolved value is equal"
bound = false
+++

Port semantic/ts consteval: resolve const strings, template literals with static parts, object literals, array and spread, across imports via the module graph, with a step budget; unresolved is a value state, not an error. Used by className and style-prop extraction. Port tests/unit/test_semantic_ts_consteval.py.
