+++
id = "01M5CH6YW8C576DAAQQ89M8282"
title = "Register GitHub Actions and Dockerfile adapters in gob-caps and gob-walk"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T11:30:11Z"
updated = "2026-10-20T13:31:56Z"
scope = ["crates/gob-caps/**", "crates/gob-symbols/src/registry.rs", "crates/gob-symbols/src/actions.rs", "crates/gob-symbols/src/dockerfile.rs", "crates/gob-symbols/src/lang.rs", "crates/gob-plan/src/catalog/answer.rs", "crates/gob-symbols/tests/it/measured.rs", "crates/gob-symbols/tests/it/snapshots/*", "docs/reference/languages.md", "docs/reference/grl/catalog.md"]

[[acceptance]]
text = "GitHub Actions and Dockerfile are matrix languages and registered adapters"
bound = true
+++

found while working ~83EFRF2: add Lang::GithubActions and Lang::Dockerfile rows to gob-caps, a path-aware LanguageHint in gob-walk, then add ACTIONS and DOCKERFILE to adapters() and BUILTIN_EXTENSIONS.
