+++
id = "01M6BFHB1VR63SY8VFQ6M9E4NB"
title = "Audit other repo-level caches (grimble-ci, gob-check, frob-check) for version-only engine fingerprint"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:57:21Z"
updated = "2026-11-01T13:42:41Z"
scope = ["crates/gob-cache/**", "crates/gob-rules/src/digest.rs", "crates/gob-rules/src/lib.rs", "crates/grimble-check/src/report_cache.rs", "crates/grimble-check/src/bind_cache.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/tests/pipeline.rs", "crates/crunk/src/cache.rs", "crates/frob-land/src/ratchet.rs", "crates/frob-check/src/lib.rs", "crates/frob-check/src/snapshot.rs", "crates/frob-ack/src/inputs.rs", "crates/gob-check/src/product.rs", "crates/frob-check/src/product.rs", "docs/design/rules.md", "changelog.d/01M6BFHB1VR63SY8VFQ6M9E4NB.fixed.md"]

[[acceptance]]
text = "each repo-level report cache is keyed on its rule table digest or documented as exempt, with a test"
bound = true
+++

Found by ~82REFNG: default_engine in gob-cache is crate version only, so rule changes without a walked-file change reuse stale reports.
