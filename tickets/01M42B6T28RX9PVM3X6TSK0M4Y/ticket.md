+++
id = "01M42B6T28RX9PVM3X6TSK0M4Y"
title = "land now takes about 10 minutes: the ratchet's base check runs cold in a fresh worktree without the shared cache"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-04T02:17:08Z"
updated = "2026-10-04T02:23:21Z"
scope = ["crates/frob-land/src/ratchet.rs", "crates/frob-land/src/land.rs", "crates/frob-land/tests/land.rs", "crates/gob-cache/**", "docs/design/rules.md"]

[[acceptance]]
text = "Given a warm primary cache and an unchanged base, when land computes the ratchet, then the base check hits the cache for unchanged files and land wall time is reported before and after"
bound = false

[[acceptance]]
text = "Given two tickets landing on the same base commit, when the second lands, then the cached base fingerprint set is reused without a base check"
bound = false
+++

Observed 2026-10-04: land of ~24K7SMT took about 10 minutes after ~QAFRXM3. The ratchet runs an unscoped check at the base commit in a throwaway detached worktree with its own empty .frob cache, plus an unscoped and a ticket-scoped check at the head; in the debug landing binary a cold full check costs minutes. The check cache is keyed by content digest (architecture.md 9), so the base run can reuse the primary checkout's cache: point the base run (and the head runs) at the repository's shared cache under the git common dir, or open the primary's .frob/cache.sqlite read-mostly, so unchanged files at base are cache hits. Also reuse the per-base fingerprint set across tickets (already cached per base oid) and run the base check only for the rules whose inputs differ between base and head where that can be proven. Measure land wall time before and after on this repository; target: land within about a minute of the head check alone.
