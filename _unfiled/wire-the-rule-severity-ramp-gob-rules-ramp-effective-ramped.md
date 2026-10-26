+++
id = "01M5WAN9GG0E1M9PM16B3EMY2Z"
title = "Wire the rule severity ramp (gob_rules::ramp effective_ramped) into each product's check pipeline"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-26T14:43:31Z"
updated = "2026-10-26T20:55:24Z"
scope = ["crates/frob-check/**", "crates/grimble-check/**", "crates/crunk-check/**", "crates/gob-rules/**", "docs/**", "Cargo.lock"]

[[acceptance]]
text = "Each product's check pipeline lowers a new-in-release rule from Error to Warn through the release line via RuleSettings::effective_ramped, with the note naming N+1, and a test per product proves it"
bound = true
+++

Follow-up of VGQ66DC: the ramp helper exists in gob-rules but no product calls it, so no real findings are ramped. Also make the ramp length configurable beyond on/off.
