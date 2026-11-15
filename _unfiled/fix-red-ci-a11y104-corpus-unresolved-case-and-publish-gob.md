+++
id = "01M7EXZ20VEG1WPQJP5TY499D4"
title = "Fix red CI: A11Y104 corpus unresolved case and publish gob-frameworks"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:22:56Z"
updated = "2026-11-15T06:22:59Z"
labels = ["no-story"]

[[acceptance]]
text = "A11Y104 corpus has an unresolved case and every_crunk_rule_has_a_corpus passes"
bound = false

[[acceptance]]
text = "gob-frameworks is publishable and the publish skip test passes"
bound = false
+++

CI run 43682380126 failed: crunk-check rule_coverage needs an unresolved case for A11Y104 in tests/mdtest/a11y104.md; gob-dev publish test fails because crunk-check now depends on gob-frameworks which is publish=false. Make gob-frameworks publishable and drop it from the skipped list.
