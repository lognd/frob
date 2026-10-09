+++
id = "01M4HDXNTJQ77R9Z81VVNK49V8"
title = "Land base-findings cache key is the crate version plus ledger config, not the engine: after a binary refresh adds rules or atoms, cached base findings omit them and every new-rule finding looks NEW, refusing every land"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-09T22:53:11Z"
updated = "2026-10-09T23:46:07Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-land/src/ratchet.rs", "crates/frob-land/tests/**", "changelog.d/**"]

[[acceptance]]
text = "Given a land after the frob binary changed (new rule or atom) and an unchanged base, when the base set is computed, then the cache misses (key includes the engine fingerprint from gob-cache, which ~EWJGM32 keys by executable content) and findings the new engine raises on the base are classified pre-existing"
bound = true
+++

logand.app-v2 F-573: refreshing to rdr-271efc66d (process.env atom live) made 16 inert env grants real; CAP001 appeared on base and every land was refused as new. Root cause: crates/frob-land/src/ratchet.rs cache_key uses CARGO_PKG_VERSION (0.532.0 for every dev build) and the ledger config only.
