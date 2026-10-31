+++
id = "01M4M2AFEZM95GY9NR98GS7YBF"
title = "gob-check owns exception binding with a default Product::resolve_exceptions (audit M4 structural half)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-10T23:28:11Z"
updated = "2026-10-31T11:43:08Z"
labels = ["no-story"]
scope = ["crates/gob-check/**", "crates/crunk-check/**", "crates/grimble-check/**"]

[[acceptance]]
text = "A default Product::resolve_exceptions in gob-check applies the product's bound exceptions"
bound = true

[[acceptance]]
text = "crunk and grimble supply hooks and no longer call apply_exceptions themselves"
bound = true
+++

found while working ~ZN62TQN: crunk already binds crunk:waive via crunk_rules::waiver (D120), so the user-visible M4 symptom is fixed. Remaining: make resolve_exceptions a provided method in gob-check that binds directives, so crunk and grimble stop duplicating apply_exceptions wiring.

no-story: internal engineering task in gob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
