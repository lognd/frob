+++
id = "01M6BFHB1VR63SY8VFQ6M9E4NB"
title = "Audit other repo-level caches (grimble-ci, gob-check, frob-check) for version-only engine fingerprint"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:57:21Z"
updated = "2026-11-01T12:40:11Z"
scope = ["crates/gob-cache/**"]

[[acceptance]]
text = "each repo-level report cache is keyed on its rule table digest or documented as exempt, with a test"
bound = false
+++

Found by ~82REFNG: default_engine in gob-cache is crate version only, so rule changes without a walked-file change reuse stale reports.
