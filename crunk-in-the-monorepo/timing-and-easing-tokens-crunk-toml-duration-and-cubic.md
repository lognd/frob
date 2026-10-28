+++
id = "01M5XCVZBYWA5WCATMF9QYZAS8"
title = "Timing and easing tokens: crunk.toml duration and cubic-bezier tokens with bound checks"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T00:41:22Z"
updated = "2026-10-28T12:55:47Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-tokens/src/dialect/timing.rs, crates/crunk-spec/src/timing.rs, crates/crunk-rules/src/token_timing.rs"]

[[acceptance]]
text = "Given a duration token of 4000ms and a configured max of 1000ms, when checked, then a TOKEN finding names the token; given a cubic-bezier with x outside 0..1, then the schema rejects it with a located error; given a valid pair, then it exports to CSS (ms, cubic-bezier()), USS and C# unchanged"
bound = false
+++

Design crunk.md section 9 item 2 and section 8 prototyping row (motion tokens, timing within token bounds). The Duration and CubicBezier value types exist in crunk-tokens model.rs; this ticket wires them through the TOML dialect, spec validation and a bounds rule. Reduced-motion twins are phase 6.

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
