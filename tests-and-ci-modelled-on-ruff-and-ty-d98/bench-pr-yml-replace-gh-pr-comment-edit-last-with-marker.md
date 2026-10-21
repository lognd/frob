+++
id = "01M5FH32Q2A4W7RBGH4THMVENY"
title = "bench-pr.yml: replace gh pr comment --edit-last with marker-based comment"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T15:25:47Z"
updated = "2026-10-21T18:24:41Z"
scope = [".github/workflows/bench-pr.yml"]

[[acceptance]]
text = "Behaviour implemented and covered by a bound test or check"
bound = true
+++

found while working ~9HS3VP7: --edit-last can clobber another job's comment
