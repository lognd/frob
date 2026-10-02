+++
id = "01M3WYJ80Y368WB0975VZZ4X9Y"
title = "gob-git LocalEdits check refuses after git checkout under core.autocrlf=true"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0030"]
labels = ["milestone:2.0.0", "component:gob-git"]
scope = ["crates/gob-git/**"]

[[acceptance]]
text = "Given a repo with core.autocrlf=true and a checked-out ledger ref, when commit_paths writes a ticket twice with a checkout in between, then the second write succeeds and a genuine local content edit still refuses"
bound = false
+++

check_local_edits in crates/gob-git/src/ledger.rs hashes raw disk bytes. With core.autocrlf=true (this host's global git config) git checkout rewrites tracked text files as CRLF, so the next commit_paths on a checked-out ref refuses with E-GIT-LOCAL-EDITS although nothing changed. Compare after applying the worktree-to-index filters (gix pipeline for the path's attributes and autocrlf) or compare normalized content, so a pure line-ending difference is never a local edit. Add a test that sets core.autocrlf=true in the temp repo config, checks out, then commits again successfully, while a real content change still refuses.
