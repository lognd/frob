+++
id = "01M30M6G3RGWFGX3HDT52EQNMR"
title = "extending guide failure-injection-acceptance-criteria.md missing registry_of_registries.json row"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5240"]
scope = ["docs/extending/registry_of_registries.json"]
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides fails: guide file docs/extending/failure-injection-acceptance-criteria.md exists on disk but has no row in registry_of_registries.json. Fix: add the missing inventory row (title/description per the existing rows' shape).
