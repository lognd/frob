+++
id = "01M4M27EJ698NR069HHC939TGD"
title = "TOOL001 compile errors from stale artifacts in a target dir shared by several worktrees (missing export of an item that exists in the source)"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-10T23:26:32Z"
updated = "2026-10-10T23:26:32Z"
scope = ["crates/gob-check/src/tools.rs"]

[[acceptance]]
text = "a tool stage that fails to compile because a shared target dir holds an artifact older than the sources is detected and rerun once, or the finding names the stale artifact, covered by a test"
bound = false
+++

found while draining tickets: with several worktrees sharing CARGO_TARGET_DIR, the clippy stage reported 'no failure_cause in the root' for code that compiled by hand; touching the crate sources fixed it. Cargo fingerprints by path, so worktrees at different commits can leave a stale artifact.
