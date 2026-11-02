+++
id = "01M6EVK4KPMKM2HCGFKSW1KHNQ"
title = "Post-commit speculative frob check races an explicit frob check for the worktree check lock"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T19:25:46Z"
updated = "2026-11-02T21:32:14Z"
scope = ["crates/frob-worktree/**", "crates/frob-check/**", "crates/frob/tests/it/doc_commands.rs", "crates/frob/tests/it/e2e_init_loop.rs", "docs/guides/ticket-branch.md"]
+++

The post-commit hook (crates/frob-worktree/src/post_commit.rs) detaches 'frob check --ticket' which holds .frob/check.lock; a user or script running 'frob check --ticket' right after 'git commit' gets E-CHECK-CONCURRENT (exit 3). Seen in CI as quickstart_runs_from_init_to_land. KG4VEGB masks it in the doc tests with FROB_NO_SPECULATIVE_CHECK=1. Fix: let an explicit check wait for or supersede the speculative one, or run the speculative check without the full-run lock.
