+++
id = "01M7E59NHR0FE608ZE2QAQ4RK9"
title = "crunk-spec: refresh snapshots and parity dumps for tokens.max_duration_ms"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-14T23:11:49Z"
updated = "2026-11-15T01:11:43Z"

[[acceptance]]
text = "crunk-spec tests pass with max_duration_ms in snapshots"
bound = false
+++

found while working YC5VP5X: inline::ok_cases_parse_cleanly and parity::every_fixture_equals_the_python_spec_dump fail on base because TOKEN010 added tokens.max_duration_ms without refreshing snapshots or *.spec.json
