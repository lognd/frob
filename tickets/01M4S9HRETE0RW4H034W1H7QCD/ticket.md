+++
id = "01M4S9HRETE0RW4H034W1H7QCD"
title = "crunk scene ingest and taffy layout solve (prerequisite of LAYOUT/RESP T1 rules)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXRHCPXFBNQDX85QY70Q62"
reporter = "lognd"
created = "2026-10-13T00:10:42Z"
updated = "2026-10-19T09:56:37Z"
scope = ["crates/crunk-ingest/**", "changelog.d/**", "docs/crunk/scene.md"]

[[acceptance]]
text = "A scene description parses to boxes and text runs and a taffy solve emits a deterministic layout-solve JSON, covered by a nextest test"
bound = true
+++

Found while attempting ~QY70Q62: crunk has no scene ingest and no taffy dependency, so the LAYOUT and RESP rules have nothing to read. Widen ~QY70Q62 scope to include crates/crunk-rules once this lands.
