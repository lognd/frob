+++
id = "01M3ZX7V587K71E94E0AE4GWW8"
title = "check --trust-from REF: trust the pairs present in the lock at a protected ref"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:33Z"
updated = "2026-10-19T08:31:39Z"
idempotency_key = "m2-sec-trust-base-ref"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/baseref.rs", "crates/gob-check/src/**", "crates/gob-trust/src/lib.rs", "crates/gob-trust/tests/baseref.rs", "crates/gob-check/Cargo.toml", "docs/design/security.md", "changelog.d/01M3ZX7V587K71E94E0AE4GWW8.*"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FTSKACE9TE7MBHQH7ET"

[[links]]
kind = "blocked-by"
target = "01M3ZX7V0XP3BYTWDHXN20Z79R"

[[acceptance]]
text = "Given a pack whose digest differs from the lock at the base ref, when check --trust-from origin/main runs, then its rules report Unresolved untrusted-in-change and the gate fails"
bound = true

[[acceptance]]
text = "Given a pack unchanged since the base ref, when check runs, then it is trusted with the effects recorded at that ref"
bound = false
+++

Implements security.md section 2.3 (base-ref trust in CI).

CI trusts exactly the (tree digest, effects) pairs in the lock read from git objects at the ref; a pack added or changed by the change under test runs with no effects and reports Unresolved untrusted-in-change, required in CI. CI never reads or writes a user store.
