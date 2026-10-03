+++
id = "01M402F2YKW1V2XRNGV1EZ3QHP"
title = "Repo-level rule results are cached by input digests only, not by the engine that produced them"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:05:54Z"
updated = "2026-10-03T05:19:31Z"
idempotency_key = "m2-cache-key-engine-version"
labels = ["milestone:2"]
scope = ["crates/gob-cache/**", "crates/gob-check/**", "crates/frob-check/**"]

[[acceptance]]
text = "Given a cached repo-level result from engine fingerprint A, when engine fingerprint B checks the same inputs, then the rule is recomputed"
bound = false
+++

Found by ~G5B3CFR: frob check reused a COV001 result computed by a different frob binary because repo-level rule results are keyed by input digests alone. After an upgrade or a worktree binary, findings can be stale and wrong (they were in the measurement). Key every cached rule result (file and repo level) by an engine fingerprint as well: binary version plus EXTRACTOR_VERSION plus the rule's version (rule metadata has one). Add a test: two engine fingerprints over the same inputs never share a cached result.
