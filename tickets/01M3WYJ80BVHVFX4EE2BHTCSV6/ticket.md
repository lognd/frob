+++
id = "01M3WYJ80BVHVFX4EE2BHTCSV6"
title = "gob-walk + gob-cache: ignore-aware walk, SQLite artifact and findings cache"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0011"]
labels = ["milestone:2.0.0", "component:gob-cache"]
scope = ["crates/gob-walk/**", "crates/gob-cache/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8044P1XYB5N4HHW33X9"

[[acceptance]]
text = "Given a repo with .gitignore excluding target/, when walked, then no path under target/ appears and the order is stable across runs"
bound = false

[[acceptance]]
text = "Given a findings entry keyed by (digest, rule, version, side-input), when any key component changes, then the lookup misses"
bound = false
+++

Implement crates/gob-walk and crates/gob-cache per architecture.md section 3 and D30. gob-walk: parallel repository walk with the ignore crate honoring .gitignore and a [check] exclude knob, returning FileEntry { path, size, blake3 digest, language guess by extension } in a deterministic order; size cap knob with Unresolved marker for oversized files. gob-cache: per-worktree SQLite at .frob/cache.sqlite (WAL, busy_timeout knob, best-effort writes logged on failure, schema versioned with migrations): tables artifacts(key = digest + producer identity, bytes), findings(file digest, rule id, rule version, side-input digest -> serialized findings), repo_rule(graph digest, rule id -> findings). API is sync; a Cache::open fails soft (returns a NullCache) when the directory is read-only. Benchmarks with criterion for walk of 10k files and 10k cache hits.
