+++
id = "01M3WYJ80V494Y7HFA43YN1JZ0"
title = "gob-git test delete_via_none_and_local_edit_refusal fails in the primary checkout"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0027"]
labels = ["milestone:2.0.0", "component:gob-git"]
scope = ["crates/gob-git/**"]

[[acceptance]]
text = "Given the primary checkout and any ticket worktree on this host, when cargo nextest run -p gob-git runs, then every test passes in both"
bound = true
+++

After landing T-0010 the test gob-git::ledger delete_via_none_and_local_edit_refusal passes in the ticket worktree but fails in the primary checkout (crates/gob-git/tests/ledger.rs line 163). The difference is environmental (the primary is the main checkout; global git config on this host sets autocrlf, and the test creates temp repos). Find the real cause, make the test independent of the host git configuration and checkout kind, and keep the LocalEdits behaviour correct.
