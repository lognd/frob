+++
id = "01M5WC3A43GMH7PY1BQW0EH8KJ"
title = "Windows: frob-worktree claim_evict an_idle_claim_is_evicted_with_the_rate_reported_and_a_repeat_needs_yes asserts rate_left 4 vs 3"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-26T15:08:39Z"
updated = "2026-10-26T15:24:09Z"
scope = ["crates/frob-worktree/**"]

[[acceptance]]
text = "The claim_evict test passes on Windows CI (rate_left matches the policy rate minus evictions inside the window) with the root cause explained in the fix"
bound = false
+++

CI run on 1f7ec48f9f, job rust (windows-latest): claim_evict.rs:243 left 4 right 3. Linux passes. Candidates: eviction-window timestamp handling or the 14-day repeat window under Windows, or clock resolution.
