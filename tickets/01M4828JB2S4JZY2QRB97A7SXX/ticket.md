+++
id = "01M4828JB2S4JZY2QRB97A7SXX"
title = "gob-symbols: TS/JS test items as units so COV001 and frob test select them"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T07:36:12Z"
updated = "2026-10-06T07:36:12Z"
scope = ["crates/gob-symbols/src/typescript/**", "crates/frob-obligations/src/cov.rs", "crates/frob-tests/src/**"]
+++

Found while working ~6KKJF80. The TS adapter marks describe/it/test calls (vitest, jest, playwright) on their apply nodes and lists them with gob_symbols::test_items, but they are not units, so calls inside a test body are attributed to the enclosing file or unit and COV001 and touched-test selection cannot name a test. Make each suite and case a unit (a symref-safe name from the title, [dupN] on repeats) with a test attribute, wire is_test for TS into the obligation code, and keep Unknown for dynamic titles (test.each).
