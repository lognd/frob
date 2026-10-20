+++
id = "01M4XK7R6QKM6CF40JCM5HEN3Y"
title = "Rust/python models mark test items so COV001 clean examples pass"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T16:16:57Z"
updated = "2026-10-14T16:16:57Z"
scope = ["crates/gob-symbols/src/**"]

[[acceptance]]
text = "COV001 examples 1 and 2 pass via run_example (test kind matches #[test] and cfg(test) items)"
bound = false
+++

Found while working ~YJPYE5V: the rust model never emits the test attr that KindTest::Test reads, so 'some t: test' is empty and COV001 always fires. Unskip examples 1,2 in crates/gob-plan/src/examples/corpus_tests.rs.
