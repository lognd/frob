+++
id = "01M4NTWET2QT576F2CHN60YHK6"
title = "TS adapter keeps a parse-error hole for MISSING nodes (const y = ;) so crunk reports the JSX syntax error"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-11T15:56:41Z"
updated = "2026-10-12T02:28:51Z"
scope = ["changelog.d/**", "crates/gob-symbols/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given `const y = ;` in a .ts file, when crunk ingests it, then a 'jsx syntax error at line 1' error is reported"
bound = true
+++

Split from ~JZPBV6H (its title/body covered sharing numeric_raw; this acceptance was the other follow-up from ~8JGRZY3).
