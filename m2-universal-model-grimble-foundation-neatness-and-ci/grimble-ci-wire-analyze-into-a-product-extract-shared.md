+++
id = "01M5F0111KG4GZSMSS7PX9D61N"
title = "grimble-ci: wire analyze into a product; extract shared verdict type from grimble-arch"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-23T08:03:29Z"
scope = ["crates/grimble-ci/**", "crates/grimble-arch/**", "crates/grimble-check/**", "Cargo.lock", "crates/grimble-verdict/**", "docs/design/boundaries.md", "docs/design/cicd.md", "crates/gob-dev/tests/layering.rs"]

[[acceptance]]
text = "grimble-ci and grimble-arch share one verdict/finding type instead of CiFinding aliasing ArchFinding, with no layering violation"
bound = true

[[acceptance]]
text = "grimble check output for arch and ci findings is unchanged (existing tests pass)"
bound = true
+++

CiFinding aliases grimble_arch::ArchFinding; extract a shared type and wire grimble-ci (and grimble-arch) into grimble check. Also generate docs/reference/rules pages (gob-dev gen rules) once wired.
