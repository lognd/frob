+++
id = "01M7EXZ20VEG1WPQJP5TY499D4"
title = "Fix red CI: A11Y104 corpus unresolved case and publish gob-frameworks"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:22:56Z"
updated = "2026-11-15T06:52:15Z"
labels = ["no-story"]
scope = ["crates/gob-frameworks/src/route_a11y.rs", "crates/crunk-check/src/route_a11y.rs", "crates/gob-frameworks/tests/it/route_a11y.rs", "crates/gob-frameworks/src/lib.rs", "crates/crunk-check/tests/mdtest/a11y104.md", "crates/gob-frameworks/Cargo.toml", "crates/gob-dev/src/publish.rs", "docs/guides/release.md", "docs/reference/rules/A11Y104.md", "crates/gob-frameworks/tests/it/main.rs"]

[[acceptance]]
text = "A11Y104 corpus has an unresolved case and every_crunk_rule_has_a_corpus passes"
bound = true

[[acceptance]]
text = "gob-frameworks is publishable and the publish skip test passes"
bound = true
+++

CI run 43682380126 failed: crunk-check rule_coverage needs an unresolved case for A11Y104 in tests/mdtest/a11y104.md; gob-dev publish test fails because crunk-check now depends on gob-frameworks which is publish=false. Make gob-frameworks publishable and drop it from the skipped list.
