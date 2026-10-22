+++
id = "01M5JQ4064A95JAP3BM4QDJRP8"
title = "crunk extract-token: promote durations once crunk.toml has a duration table"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-10-22T21:08:52Z"
updated = "2026-10-22T21:08:52Z"
scope = ["crates/crunk-spec/**", "crates/crunk/src/extract.rs"]

[[acceptance]]
text = "Given a duration literal such as 200ms, when crunk extract-token runs, then it is promoted to a duration token and references are rewritten"
bound = false
+++

found while working K4DBBVJ: durations are currently refused with E-EXTRACT-DURATION because crunk.toml has no duration table. Also candidates: percent and em kinds, JSX string literal rewriting.
