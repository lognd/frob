+++
id = "01M5XCYCSXSPQP9A4DZKNX5RGS"
title = "Research artifacts: design/research/*.md front matter, personas/*.toml, journeys/*.toml with UX evidence rules"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:42:41Z"
updated = "2026-10-27T00:43:02Z"
labels = ["area:crunk"]
scope = ["crates/crunk-spec/src/research.rs, crates/crunk-rules/src/ux/research.rs, crates/crunk-rules/tests/ux_research.rs"]

[[acceptance]]
text = "Given a persona or journey without cited evidence, when checked, then a UX finding names it; given a screen citing no persona or job, then a UX finding fires; given research older than the configured staleness window, then a stale finding fires. Edge cases: a citation to a missing research file is a dangling-reference finding; front matter missing or malformed YAML is a located schema error; an empty research dir with the pack enabled is silent; duplicate persona ids are refused"
bound = false
+++

Design crunk.md section 8 research row. Opt-in per project. Reuses crunk-spec load patterns from screen_file.rs.
