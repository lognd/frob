+++
id = "01M4DPJKMT0JYSBXXXHPSJRG93"
title = "frob test in a ticket worktree says 'not in a lease-holding worktree; no evidence recorded'"
type = "bug"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T12:07:28Z"
updated = "2026-10-08T12:07:28Z"
scope = ["changelog.d/**", "crates/frob-tests/**", "crates/frob-lease/**"]

[[acceptance]]
text = "Given a leased ticket worktree, when frob test runs, then it records evidence for that ticket"
bound = false
+++

Follow-up from ~9X572Y1.
