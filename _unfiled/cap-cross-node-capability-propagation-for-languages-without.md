+++
id = "01M65Q2GK3CZT64EQXYTH00NBC"
title = "CAP: cross-node capability propagation for languages without a capability binder, and module-level callee code"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-30T06:13:38Z"
updated = "2026-10-30T06:13:38Z"
+++

Found while working 01M642304NQ5XQP3WWD0T8Z2BM. Cross-node propagation covers Python, TS/JS, C# and Rust. Not covered: other languages (no capability binder), module-level code of a callee file, and constructor calls over-approximate nested method uses.
