+++
id = "01M4V9EAS5J8443PRPX5HAB4C2"
title = "frob-gh: GitHub HTTPS client crate (removed, no consumer)"
type = "chore"
category = "done"
outcome = "wont-fix"
priority = "low"
reporter = "lognd"
created = "2026-10-13T18:47:18Z"
updated = "2026-10-13T18:47:22Z"
+++

Dropped by ~7TH24RC: ~GHMWDGG chose frob-release::ci for CI reads, so frob-gh had no consumer and carried a heavy reqwest/rustls/tokio tree. Re-add when a Milestone 2 PR/CI-status feature needs it (docs/design/git-io.md section 4).
