+++
id = "01M6SNTWBS6DV2VMAPQASQ6BMN"
title = "grimble-lints: migrate err family to the universal model"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-07T00:16:47Z"
updated = "2026-11-07T00:49:29Z"
scope = ["crates/grimble-lints/src/**", "docs/design/grimble/lint-classification.md", "changelog.d/*ASQ6BMN*", "docs/README.md", "crates/grimble-lints/tests/**", "crates/grimble-lints/Cargo.toml"]

[[acceptance]]
text = "ERR001-003 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
