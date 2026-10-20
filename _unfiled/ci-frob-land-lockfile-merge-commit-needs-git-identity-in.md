+++
id = "01M50C2K3H0STZWFR5P29BWY8G"
title = "ci: frob-land lockfile merge commit needs git identity in test env"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-15T18:09:32Z"
updated = "2026-10-15T18:28:19Z"
scope = ["crates/frob-land/src/lockfile.rs"]

[[acceptance]]
text = "test passes with no global git identity"
bound = true
+++

candidate::tests::disjoint_tickets_that_both_change_cargo_lock_merge fails on CI with 'Author identity unknown' when committing the lockfile merge (E-LAND-LOCKFILE). Make the production commit supply an explicit frob identity via -c user.name/user.email (or GIT_* env) so it never depends on ambient git config.
