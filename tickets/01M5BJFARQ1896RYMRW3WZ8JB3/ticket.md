+++
id = "01M5BJFARQ1896RYMRW3WZ8JB3"
title = "Mark lexical rules needs = Lexical and add their opaque_fire island cases"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T02:32:59Z"
updated = "2026-10-20T03:03:20Z"
scope = ["crates/*/src/rules/**", "crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-check/tests/mdtest/tick004.md", "crates/frob-check/tests/mdtest/tick005.md", "docs/reference/rules/TICK004.md", "docs/reference/rules/TICK005.md"]

[[acceptance]]
text = "TICK004 and TICK005 declare needs = Lexical and each has an expect=fire cell=island mdtest block; the frob rule coverage check passes"
bound = true
+++

~NWVJYJ5 added RuleMeta needs and the opaque_fire case kind; no rule declares needs = Lexical yet. Classify text-only rules and add expect=fire cell=island blocks (or allowlist entries with tickets).
