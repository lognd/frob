+++
id = "01M691E42SHR7Y24MC947J2A5Z"
title = "gob-rules assert_unique hits const-eval limit with 10 more grimble rules"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-31T13:12:27Z"
updated = "2026-10-31T13:12:27Z"
scope = ["crates/gob-rules/**"]
+++

found while working ~VKN98M6: frob-docgen fails to compile (long_running_const_eval at crates/gob-rules/src/index.rs:70) once MDL022-MDL031 are registered, so gen all cannot run. Fix: make assert_unique cheaper or allow the lint.
