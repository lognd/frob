+++
id = "01M48PBYN43QPHGAF7Y14C4ZGJ"
title = "gob-diagnostics: render fix edits as a diff with the applicability tier in the text renderer"
type = "story"
category = "todo"
priority = "high"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:38Z"
updated = "2026-10-06T13:41:06Z"
scope = ["crates/gob-diagnostics/**"]

[[acceptance]]
text = "a fixable toy rule produces a rendering that contains the diff and the tier (snapshot)"
bound = false

[[acceptance]]
text = "changing an edit fails that snapshot"
bound = false

[[acceptance]]
text = "JSON output is unchanged"
bound = false

[[acceptance]]
text = "the text renderer also shows an Unresolved finding's reason in words and its remedy, and JSON carries reason"
bound = false
+++

The text renderer prints only `fix: <title>` (crates/gob-diagnostics/src/text.rs:163). Render each fix as a unified diff of its edits with the tier (safe/unsafe/display-only) and a note for unsafe tiers, the way ruff renders fixes in its mdtest snapshots, so one snapshot asserts message, span and fix. Source: notes/research/rule-testing.md (D103).
