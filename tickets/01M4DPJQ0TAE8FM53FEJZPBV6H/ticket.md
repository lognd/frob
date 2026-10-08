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
updated = "2026-10-08T12:07:32Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given const y = ;, when parsed, then a parse-error hole exists and crunk reports the JSX syntax error"
bound = false
+++

Follow-ups from ~8JGRZY3.
