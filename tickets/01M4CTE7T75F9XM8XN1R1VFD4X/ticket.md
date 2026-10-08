+++
id = "01M4CTE7T75F9XM8XN1R1VFD4X"
title = "Per-command Session: open repository, ledger, leases and config once and pass it to verbs; one Workspace type (audit M14)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:45Z"
updated = "2026-10-08T03:57:28Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/gob-cli/**", "crates/frob-land/**", "crates/frob-lease/**"]

[[links]]
kind = "blocked-by"
target = "01M4CTE6TNY9C5R18NE53J42W1"

[[acceptance]]
text = "Given frob land, when it runs, then the repository is opened once (counter test)"
bound = false
+++

notes/review/audit-2026-10-07.md M14: three Workspace types, verbs open the repository 47 times (8 in land). Do after the Config Document ticket.
