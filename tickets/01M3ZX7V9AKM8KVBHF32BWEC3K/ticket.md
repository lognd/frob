+++
id = "01M3ZX7V9AKM8KVBHF32BWEC3K"
title = "trust --follow: trust pairs reachable on a fetched protected branch"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-03T03:34:34Z"
idempotency_key = "m2-sec-trust-follow"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-trust/src/follow.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7V0XP3BYTWDHXN20Z79R"

[[links]]
kind = "blocked-by"
target = "01M3ZX7V587K71E94E0AE4GWW8"

[[acceptance]]
text = "Given `trust --follow origin/main`, when a pack changes on origin/main and is fetched, then the new pair is trusted with no prompt"
bound = false

[[acceptance]]
text = "Given a pair present only in an unpushed commit, when consulted, then it is untrusted"
bound = false
+++

Implements security.md section 2.3 (follow a protected branch).

Run once per repository; any (digest, effects) pair in the lock at a commit reachable from the fetched protected ref is trusted without a prompt.
