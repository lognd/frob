## Done report

gob-walk and gob-cache per architecture.md section 3 and D30: ignore-crate parallel walk honoring gitignore plus config excludes, blake3 digests, language hints, deterministic order, oversized reporting; rusqlite WAL cache at <dir>/cache.sqlite with busy_timeout, schema_version migrations, artifacts/findings/repo_rule tables keyed exactly as D30 states, best-effort writes, NullCache fallback, stats for doctor; criterion benches for a 10k-file walk and 10k cache hits. Deviations: walk returns Result (invalid exclude glob is E-WALK-GLOB); the file is cache.sqlite where architecture.md says cache.db (design doc to reconcile); single connection behind a Mutex instead of a reader pool plus writer channel; knob names for exclude, size cap and busy_timeout are owned by gob-config later.

### Changed
```
 Cargo.lock                        | 663 ++++++++++++++++++++++++++++++++++++++
 crates/gob-cache/Cargo.toml       |  26 ++
 crates/gob-cache/benches/cache.rs |  35 ++
 crates/gob-cache/src/lib.rs       | 400 +++++++++++++++++++++++
 crates/gob-walk/Cargo.toml        |  27 ++
 crates/gob-walk/benches/walk.rs   |  24 ++
 crates/gob-walk/src/lib.rs        | 330 +++++++++++++++++++
 tickets/T-0011/ticket.md          |   6 +-
 8 files changed, 1508 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)
