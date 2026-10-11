+++
id = "01M4DPJQ0TAE8FM53FEJZPBV6H"
title = "Share numeric_raw and the React unitless list from gob-symbols; TS adapter keeps a hole for MISSING nodes"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:07:32Z"
updated = "2026-10-11T15:56:41Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given a numeric style value, when crunk-ingest lowers it, then it uses gob_symbols::numeric_raw and the single gob_symbols unitless list (no duplicate list in crunk-ingest)"
bound = false
+++

Follow-ups from ~8JGRZY3.
