+++
id = "01M5XCYCP797Z6M8WPBW7FAD5W"
title = "Project phase in crunk.toml (discovery|alpha|beta|live) selects a lint profile"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:42:41Z"
updated = "2026-10-27T00:42:41Z"
labels = ["area:crunk"]
scope = ["crates/crunk-spec/src/phase.rs, crates/crunk-rules/src/phase_profile.rs, crates/crunk-rules/tests/phase_profile.rs"]

[[acceptance]]
text = 'Given phase = "alpha", when checked, then only structure lints run and HUMAN001 plus the full A11Y set are listed as not applicable; given beta, then the full A11Y set and HUMAN001 run; given live, then metrics and experiment rules also run. Edge cases: an unknown phase value is a located schema error listing the four values; an absent phase defaults to beta and says so in the envelope; an explicit [lint] setting overrides the profile; phase changes are logged'
bound = false
+++

Design crunk.md section 8 first row. Opt-in: no phase means current behaviour unchanged.
