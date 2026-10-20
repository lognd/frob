+++
id = "01M4M2AFEZM95GY9NR98GS7YBF"
title = "gob-check owns exception binding with a default Product::resolve_exceptions (audit M4 structural half)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-10T23:28:11Z"
updated = "2026-10-10T23:28:11Z"
scope = ["crates/gob-check/**,crates/crunk-check/**,crates/grimble-check/**"]
+++

found while working ~ZN62TQN: crunk already binds crunk:waive via crunk_rules::waiver (D120), so the user-visible M4 symptom is fixed. Remaining: make resolve_exceptions a provided method in gob-check that binds directives, so crunk and grimble stop duplicating apply_exceptions wiring.
