+++
id = "01M43FX5KWVP277RX5666MMPM1"
title = "land leaves a conflicted merge in the worktree and reports E-CONFIG instead of a conflict"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-04T12:58:30Z"
updated = "2026-10-04T13:48:15Z"
scope = ["crates/frob-land/src/land.rs", "crates/frob-land/tests/land.rs", "docs/design/tickets.md", "crates/frob-land/src/lockfile.rs", "crates/gob-config/src/load.rs", "crates/gob-config/src/lib.rs", "crates/frob-land/Cargo.toml"]

[[acceptance]]
text = "Given a ticket branch whose refresh merge with the trunk conflicts, when land runs, then it refuses with a conflict error listing the conflicted paths"
bound = true

[[acceptance]]
text = "Given that refusal, when the worktree is inspected, then no merge is in progress and the branch head and index are unchanged"
bound = true
+++

Observed 2026-10-04 landing ~M525Y1M: experimental had changed [evidence] allowed_tools in frob.toml, the ticket branch changed the same line. land merged experimental into the ticket branch, the merge conflicted, and land then tried to load the worktree frob.toml with conflict markers and failed with E-CONFIG (TOML parse error at the <<<<<<< line). The worktree was left mid-merge with unmerged paths. Expected: a conflicting refresh merge is detected before any config is read from the worktree, the merge is aborted so the worktree is exactly as before, and land refuses with a dedicated conflict error naming the unmerged paths and the remedy (resolve on the branch, then land again).
