+++
id = "01M7EXVWAQAC055HACEB8MBHVT"
title = "frob tool outdated: report pinned vs latest tool versions (opt-in network)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:12Z"
updated = "2026-11-15T06:21:17Z"
idempotency_key = "static-research-k15"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXT3X9DSSHYJWNQ4ZQPV00"

[[acceptance]]
text = "outdated lists stages whose pinned version is behind latest, using an injectable version source in tests"
bound = false

[[acceptance]]
text = "Without the explicit command no network access happens"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 13 (split off), section 4.2. Rationale: version drift between pinned_version and upstream is invisible. Remedy: frob tool outdated compares each stage's pinned_version/range with the latest published version, network only when invoked explicitly. Blocked by the frob tool verb ticket. Latest-version sources per ecosystem are [M]: verify first. Crates/files: crates/frob (tool verb), crates/gob-check/src/tool_def.rs.
