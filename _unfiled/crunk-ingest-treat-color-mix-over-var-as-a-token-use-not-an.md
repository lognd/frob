+++
id = "01M6Z4RGT1BGP5V2SN4KAVWFAE"
title = "crunk-ingest: treat color-mix() over var() as a token use, not an unreadable colour"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-09T03:13:51Z"
updated = "2026-11-09T03:13:51Z"
scope = ["crates/crunk-ingest/**"]
+++

found while working 1EYXGVV: COLOR001 translucent fix emits color-mix(in srgb, var(--t) N%, transparent); facts.rs flags it unreadable_colors so re-check reports Unresolved.
