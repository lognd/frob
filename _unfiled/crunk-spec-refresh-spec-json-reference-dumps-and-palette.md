+++
id = "01M7GGAD1YP6669CPQPTGRG083"
title = "crunk-spec: refresh spec.json reference dumps and palette snapshot for the durations scale"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-11-15T21:02:57Z"
updated = "2026-11-15T21:10:22Z"
scope = ["crates/crunk-spec/tests/**"]

[[acceptance]]
text = "every_fixture_equals_the_python_spec_dump passes with the durations scale and duration token"
bound = true

[[acceptance]]
text = "inline::ok_cases_parse_cleanly passes with refreshed snapshots"
bound = true
+++

CI on experimental 64e2aa59f2 fails on ubuntu and windows: full_all_tables lacks scales.durations [] and tokens.duration, added by 939491c48b. Update reference dumps and insta snapshots; no src changes.
