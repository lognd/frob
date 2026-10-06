+++
id = "01M49SWMDMB1TEHJ5Q1HRJ3KXT"
title = "test-dry-run fails on goway helpers: E-TESTS-GIT Could not create index from tree"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T23:48:25Z"
updated = "2026-10-06T23:48:25Z"
scope = ["crates/frob-tests/**", "crates/gob-git/**"]

[[acceptance]]
text = "test-dry-run passes on a goway helper for a branch several commits ahead of origin/experimental"
bound = false

[[acceptance]]
text = "on a shallow clone without the base objects frob test reports a named reason, not a generic git error"
bound = false
+++

Seen twice on 2026-10-06 (~N88H9SY's remote cargo dev ci, before and after a merge; the step passed remotely earlier the same day for ~FWSQYH1 and ~AVXTRHX): frob test --dry-run against origin/experimental fails with E-TESTS-GIT 'Could not create index from tree' on the helper. goway sends a minimal .git with HEAD and the with_refs refs (refs/heads/experimental, refs/remotes/origin/experimental) and only the objects of each ref's tip tree, shallow. Find whether frob test needs the merge base or the base tree's index entries that a shallow overlay lacks, then either have goway send what frob test needs or make frob test report a named Unresolved (not E-TESTS-GIT) when the base history is shallow.
