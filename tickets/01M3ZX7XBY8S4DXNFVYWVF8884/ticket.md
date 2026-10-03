+++
id = "01M3ZX7XBY8S4DXNFVYWVF8884"
title = "Effective policy snapshot at a ref"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:36Z"
updated = "2026-10-03T03:34:36Z"
idempotency_key = "m2-sec-policy-snapshot"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/policy/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FTSKACE9TE7MBHQH7ET"

[[links]]
kind = "blocked-by"
target = "01M3ZX7JWHQZQHD66HV2SB0498"

[[acceptance]]
text = "Given two refs differing in a disabled rule and a widened exclude, when snapshots are diffed, then both changes appear with old and new values"
bound = false

[[acceptance]]
text = "Given identical policy, when diffed, then the delta is empty"
bound = false
+++

Implements security.md section 2.7 (GATE001 inputs).

Compute the effective policy at base and head: packs and paths, severities, disabled rules, fail_on*, [compute], excludes, grants, replaces, trust settings, repository-adapter NotApplicable claims, in-source declarations a P+ verdict depends on.
