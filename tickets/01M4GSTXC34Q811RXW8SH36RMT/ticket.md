+++
id = "01M4GSTXC34Q811RXW8SH36RMT"
title = "ref_mode = branch with a detached HEAD gives E-LEDGER-DETACHED even for read-only verbs (doctor, check), and every CI pull_request checkout is detached"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T17:02:09Z"
updated = "2026-10-10T20:41:57Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-ledger/**", "crates/frob/**", "changelog.d/**"]

[[acceptance]]
text = "Given ref_mode = branch and a detached HEAD at origin/main, when frob ticket doctor or frob check runs, then it reads the ledger from the configured ticket ref without requiring a branch; only writing verbs refuse, with a remedy"
bound = false
+++

hullbreach platform repro: git checkout --detach origin/main; frob ticket doctor. Workaround: git switch -C ci-check.
