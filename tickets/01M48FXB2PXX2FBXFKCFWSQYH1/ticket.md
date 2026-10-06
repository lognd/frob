+++
id = "01M48FXB2PXX2FBXFKCFWSQYH1"
title = "crunk-check: first web rule over markup, style and class_tokens (className tokens against CSS declarations and custom properties)"
type = "task"
category = "in-progress"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:48Z"
updated = "2026-10-06T12:02:20Z"
scope = ["crates/crunk-check/**"]
+++

crunk check runs over the shared TSX/CSS fixture with an empty rule list (crates/frob/tests/web_conformance.rs asserts rules == []). The first rule should read gob_ir markup/style and class tokens, and replace that assertion. Found while working ~4M1BX5H.
