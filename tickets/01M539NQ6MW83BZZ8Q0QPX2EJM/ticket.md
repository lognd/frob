+++
id = "01M539NQ6MW83BZZ8Q0QPX2EJM"
title = "GRL examples: rust/python adapters emit the test attr (subset of COV001 examples 1 and 2)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T21:25:16Z"
updated = "2026-10-16T21:53:29Z"
scope = ["crates/gob-symbols/**", "crates/gob-plan/tests/ten_rules/**"]

[[acceptance]]
text = "Rust #[test] fns and cfg(test) modules and python test_* functions carry unit attr test=true"
bound = true
+++

Split from ~C6ZSWB2: the example model needs the rust cfg(test)/#[test] and python test_ marks (attr test) so COV001 clean passes, and unresolved marking for the dynamic call. Remove COV001 1/2 from KNOWN_ENGINE_GAPS.
