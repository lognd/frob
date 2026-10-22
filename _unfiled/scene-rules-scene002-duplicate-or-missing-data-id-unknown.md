+++
id = "01M5H30AQNZSC77EY70P28KM3V"
title = "Scene rules SCENE002+: duplicate or missing data-id, unknown tags, at-rules (crunk-scene already exposes them)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T05:58:06Z"
updated = "2026-10-22T22:28:13Z"
scope = ["crates/crunk-rules/**", "crates/crunk-scene/**", "docs/crunk/rules/**", "docs/reference/rules/**", "docs/design/crunk.md"]

[[acceptance]]
text = "SCENE002 flags a duplicate or missing data-id in a scene, with a failing and a passing test"
bound = true

[[acceptance]]
text = "SCENE003 flags unknown tags and SCENE004 flags unsupported at-rules, each with a failing and a passing test"
bound = true
+++
