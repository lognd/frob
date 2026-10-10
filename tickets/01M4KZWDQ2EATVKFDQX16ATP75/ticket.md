+++
id = "01M4KZWDQ2EATVKFDQX16ATP75"
title = "base-ref config tests commit without an identity and fail NoIdentity on CI"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-10T22:45:34Z"
updated = "2026-10-10T22:47:17Z"
scope = ["crates/frob-lease/tests/lease.rs", "crates/frob-pm/tests/config.rs"]

[[acceptance]]
text = "lease_config_reads_the_base_ref_over_a_stale_worktree_copy passes with no global git identity"
bound = false

[[acceptance]]
text = "repo_wide_tables_come_from_the_base_ref_over_a_stale_worktree_copy passes with no global git identity"
bound = false
+++

The tests write [user] into the repo config after Repo::init, but a handle snapshots config when opened, so the library commit sees no identity (commit: NoIdentity) on runners without a global identity. Pass the author through CommitOptions instead.
