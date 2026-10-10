+++
id = "01M4GZMQ4AC12A6E45FGZ4NM0Y"
title = "TOOL001 pre-existing match is keyed on the raw failure excerpt, so a tool stage already red on the base is NEW on every land when its output varies (timings, ordering)"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-09T18:43:37Z"
updated = "2026-10-10T02:56:41Z"
labels = ["adoption:logand-app", "creates:crates/gob-check/src/tool_key.rs"]
scope = ["changelog.d/**", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/lib.rs", "crates/gob-check/src/tool_key.rs"]

[[acceptance]]
text = "Given a tool stage that fails on the base and on the ticket with differently worded output (vitest timings, ordering, counts), when land classifies findings, then the TOOL001 finding is pre-existing: tool-stage findings are fingerprinted by (stage, exit class) or by the parsed structured failure ids, never by excerpt text"
bound = true
+++

logand.app-v2 F-569/F-570: ~1N17XF3 (backend-only) refused 3 times by a frontend vitest stage already red on main. The 'do not gate a ticket on a stage whose inputs it does not touch' half is in the fast-lands work (~RDRSZC5).
