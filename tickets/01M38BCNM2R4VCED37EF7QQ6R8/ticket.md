+++
id = "01M38BCNM2R4VCED37EF7QQ6R8"
title = "Register crunk as REQUIRED_FOR_FAMILY tool for LAYOUT"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5762"]
labels = ["milestone:v0.537.0"]
scope = ["src/frob/doctor.py", "tests/unit/test_doctor.py", "docs/modules/doctor.md"]

[[links]]
kind = "blocked-by"
target = "01M38BCNM4HDFSRX2FT62PEV5A"
+++

Register crunk as a REQUIRED_FOR_FAMILY tool for the LAYOUT family: _FAMILY_TOOL_RELEVANCE entry plus relevance predicate in doctor.py (no never-fail override, per T-5335).

Positive control: on a fixture repo with gallery org buckets declared but no crunk binary on PATH, scan_external_tools returns a FAILING finding; removing the buckets makes it silent.

Doc page: docs/modules/doctor.md#required-for-family

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
