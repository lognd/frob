+++
id = "01M4S9C3K5QX5Y365RBRJ1KRP5"
title = "crunk tokens: unknown --target exits 0 instead of usage 2"
type = "bug"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-13T00:07:37Z"
updated = "2026-10-13T03:05:27Z"
scope = ["crates/crunk/**"]

[[acceptance]]
text = "Given an unknown --target value, when crunk tokens runs, then it exits 2 with a usage error"
bound = false
+++

found while working ~C78QET8: test an_unknown_target_is_a_usage_error_and_a_bad_spec_is_a_refusal (crates/crunk/tests/tokens.rs:160) fails, left 0 right 2
