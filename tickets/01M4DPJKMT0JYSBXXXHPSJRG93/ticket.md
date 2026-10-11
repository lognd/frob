+++
id = "01M4DPJKMT0JYSBXXXHPSJRG93"
title = "frob test in a ticket worktree says 'not in a lease-holding worktree; no evidence recorded'"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T12:07:28Z"
updated = "2026-10-11T03:57:59Z"
scope = ["changelog.d/**", "crates/frob-tests/**", "crates/frob-lease/**"]

[[acceptance]]
text = "Given a linked ticket worktree holding a lease, when frob-tests looks up the lease for that worktree from the repository common dir, then it returns the leased ticket (test a_linked_worktree_finds_the_lease_it_holds); a real frob test run in a leased worktree recorded evidence for the ticket (no 'not in a lease-holding worktree' warning)"
bound = true
+++

Follow-up from ~9X572Y1.
