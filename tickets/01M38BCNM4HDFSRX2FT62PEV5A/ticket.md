+++
id = "01M38BCNM4HDFSRX2FT62PEV5A"
title = "Vendor crunk's gallery manifest schema for frob-side validation"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5764"]
labels = ["milestone:v0.537.0"]
scope = ["src/frob/webapp/_gallery_schema.py", "tests/unit/test_webapp_gallery_schema.py", "tests/fixtures/webapp/gallery/", "docs/modules/webapp-layout.md"]
+++

Vendor and pin crunk's gallery manifest JSON schema into frob for frob-side validation.

Positive control: load crunk's fixture manifest through frob's vendored validator; a manifest missing source_hash is rejected identically to crunk's own check.

Doc page: docs/modules/webapp-layout.md#manifest

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
