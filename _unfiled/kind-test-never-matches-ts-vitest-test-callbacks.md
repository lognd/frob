+++
id = "01M5P621KV0Y3BRPBFQWVRAYZ5"
title = "kind test never matches TS vitest test() callbacks"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-24T05:27:40Z"
updated = "2026-10-24T06:45:23Z"
scope = ["crates/gob-plan/src/exec/core/kind.rs", "crates/gob-symbols/src/typescript/fold.rs"]

[[acceptance]]
text = "A vitest test() callback in a TS file is matched by the test kind and covered by a nextest test"
bound = false
+++

found while working ~GNC7N38. TS fold marks test()/it() units with an attr("test") child node carrying a keyword role, but KindTest::Test in kind.rs only matches unit attrs test=Bool(true), so 'inside test' never matches a TS test callback. Align one side.
