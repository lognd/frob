+++
id = "01M6SNTWBS6DV2VMAPQASQ6BMN"
title = "grimble-lints: migrate err family to the universal model"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-07T00:16:47Z"
updated = "2026-11-07T01:26:48Z"
scope = ["crates/grimble-lints/src/**", "docs/design/grimble/lint-classification.md", "changelog.d/*ASQ6BMN*", "docs/README.md", "crates/grimble-lints/tests/**", "crates/grimble-lints/Cargo.toml"]

[[acceptance]]
text = "ERR001-003 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = true

[[acceptance]]
text = "ERR001-003 discover sites from the universal model; the err_pass integration tests pass"
bound = true

[[acceptance]]
text = "lint-classification.md records the err slice and the missing U queries"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
