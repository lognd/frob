+++
id = "01M47QTVCF0WDJWM22AG4WAFJT"
title = "Fix snapshots and fixpoint convergence for every fixable rule"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T04:34:00Z"
updated = "2026-10-06T13:41:07Z"
scope = ["crates/gob-fix/**", "crates/gob-mdtest/**"]

[[links]]
kind = "blocked-by"
target = "01M43ARX0JB4A8E1YW329MKDDF"

[[links]]
kind = "blocked-by"
target = "01M48PBYN43QPHGAF7Y14C4ZGJ"

[[acceptance]]
text = "each fixable rule has a fix diff snapshot"
bound = false

[[acceptance]]
text = "a fix that breaks parsing or oscillates fails the harness in a self-test"
bound = false

[[acceptance]]
text = "after each fix round parse status and opaque or hole counts never degrade, and no finding changes class from fire to unresolved"
bound = false

[[acceptance]]
text = "a self-test where a fix wraps code in a macro (fire becomes opaque) fails"
bound = false
+++

build-test-ci.md section 6, ruff's test harness. On top of gob-fix (~29MKDDF): for each fixable rule's fixtures, apply fixes to a fixpoint (at most 10 rounds), snapshot the unified diff, and fail if a round introduces a parse error, the fixpoint is not reached, or a fixable finding remains.
