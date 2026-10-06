+++
id = "01M4828JB2S4JZY2QRB97A7SXX"
title = "gob-symbols: TS/JS test items as units so COV001 and frob test select them"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T07:36:12Z"
updated = "2026-10-06T13:46:52Z"
scope = ["crates/gob-symbols/src/typescript/**", "crates/frob-obligations/src/cov.rs", "crates/frob-tests/src/**", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/tests/typescript.rs", "crates/gob-symbols/tests/snapshots/**", "crates/gob-symbols/tests/corpus/**", "crates/frob/tests/web_conformance.rs"]

[[acceptance]]
text = "Each recognised describe/it/test call is a function unit (suite$title or test$title, [dupN] on repeats) and calls in its callback are attributed to it"
bound = true

[[acceptance]]
text = "is_typescript_test_fn names TS test units and frob-tests is_test_fn and COV001 use it; dynamic titles stay Unknown (no unit)"
bound = true

[[acceptance]]
text = "EXTRACTOR_VERSION is bumped for the changed per-file output"
bound = true
+++

Found while working ~6KKJF80. The TS adapter marks describe/it/test calls (vitest, jest, playwright) on their apply nodes and lists them with gob_symbols::test_items, but they are not units, so calls inside a test body are attributed to the enclosing file or unit and COV001 and touched-test selection cannot name a test. Make each suite and case a unit (a symref-safe name from the title, [dupN] on repeats) with a test attribute, wire is_test for TS into the obligation code, and keep Unknown for dynamic titles (test.each).
