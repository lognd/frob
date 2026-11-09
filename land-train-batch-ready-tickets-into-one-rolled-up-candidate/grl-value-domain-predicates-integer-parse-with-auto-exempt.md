+++
id = "01M5ETSE956ZY0S15CMQGH367X"
title = "GRL value-domain predicates: integer parse with auto exempt, set membership, BEM segment split and per-segment case"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-21T08:56:03Z"
updated = "2026-11-09T17:37:43Z"
scope = ["crates/gob-plan/src/**", "crates/gob-plan/tests/**", "docs/design/shared/grl-spec.md/**", "docs/reference/grl/**", "packs/crunk-core/exceptions.toml/**", "docs/design/shared/grl-spec.md", "packs/crunk-core/exceptions.toml"]
+++

Split from ~CZSG7YJ. Needed for LAYER001 (integer value in config.layers set, auto exempt) and ORG002 (class_selector BEM segment split, case per config.org.class_case).
