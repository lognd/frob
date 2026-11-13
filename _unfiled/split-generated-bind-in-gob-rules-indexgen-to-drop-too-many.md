+++
id = "01M7A4G1C8YMH3JECJ8TXD3QMN"
title = "Split generated bind() in gob-rules indexgen to drop too_many_lines allow"
type = "task"
category = "in-progress"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-11-13T09:40:52Z"
updated = "2026-11-13T12:57:23Z"
labels = ["no-story", "creates:crates/gob-rules/**"]
scope = ["crates/gob-rules/**", "crates/grimble-model/src/rules/**", "crates/crunk-rules/**"]

[[acceptance]]
text = "Given a rule crate with more than 40 rules, when its index is generated, then bind is split into BindPart chunks and no too_many_lines allow is needed"
bound = false
+++
