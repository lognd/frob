+++
id = "01M5XCYCSXSPQP9A4DZKNX5RGS"
title = "Research artifacts: design/research/*.md front matter, personas/*.toml, journeys/*.toml with UX evidence rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:42:41Z"
updated = "2026-11-16T13:39:13Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-spec/src/research.rs, crates/crunk-rules/src/ux/research.rs, crates/crunk-rules/tests/ux_research.rs", "crates/crunk-spec/src/research.rs", "crates/crunk-spec/src/lib.rs", "crates/crunk-rules/src/ux/research.rs", "crates/crunk-rules/src/ux/mod.rs", "crates/crunk-rules/tests/it/ux_research.rs", "crates/crunk-rules/tests/it/main.rs"]

[[acceptance]]
text = "Given a persona or journey without cited evidence, when checked, then a UX finding names it; given a screen citing no persona or job, then a UX finding fires; given research older than the configured staleness window, then a stale finding fires. Edge cases: a citation to a missing research file is a dangling-reference finding; front matter missing or malformed YAML is a located schema error; an empty research dir with the pack enabled is silent; duplicate persona ids are refused"
bound = true
+++

Design crunk.md section 8 research row. Opt-in per project. Reuses crunk-spec load patterns from screen_file.rs.

no-story: internal engineering task in crunk-spec; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
