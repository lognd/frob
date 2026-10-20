+++
id = "01M38BCNM7VWPGK41BXPGC5XVM"
title = "LAYOUT001-00x: render-exists, review-current (source_hash), unreviewed=fail"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5767"]
labels = ["milestone:v0.537.0"]
scope = ["src/frob/gates/_layout_gate.py", "src/frob/webapp/_layout_structure.py", "tests/unit/test_layout_gate.py", "tests/fixtures/webapp/layout1xx/", "docs/modules/webapp-layout-structure.md"]

[[links]]
kind = "blocked-by"
target = "01M38BCNM4HDFSRX2FT62PEV5A"
+++

LAYOUT001-00x rules: render-exists, review-current (manifest source_hash matches current source and fixture props byte hash, owner decision Q3), unreviewed (verdict null) = fail. New gate module reusing the A11Y auto-discovery pattern.

Positive control: a fixture manifest entry with source_hash mismatch vs current file content raises LAYOUT002; a verdict=null entry raises LAYOUT001; both clear once real.

Doc page: docs/modules/webapp-layout-structure.md

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
