+++
id = "01M4FD03W4D4XZZ3XBP32Q9XFQ"
title = "frob init on a non-main branch writes [tickets] ref = the current branch instead of the base branch"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T03:58:34Z"
updated = "2026-10-10T19:47:49Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob/**", "crates/frob-ledger/**", "changelog.d/**"]

[[acceptance]]
text = "Given a repository on a feature branch with main as default branch, when frob init runs, then [tickets] ref names refs/heads/main (the remote default or main), and an explicit flag overrides it"
bound = false
+++

Hullbreach platform repro on branch lognd/frob-v2-migration.
