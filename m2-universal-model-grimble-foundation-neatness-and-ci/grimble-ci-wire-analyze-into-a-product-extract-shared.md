+++
id = "01M5F0111KG4GZSMSS7PX9D61N"
title = "grimble-ci: wire analyze into a product; extract shared verdict type from grimble-arch"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-23T07:45:50Z"
scope = ["crates/grimble-ci/**", "crates/grimble-arch/**", "crates/grimble-check/**", "Cargo.lock", "crates/grimble-verdict/**"]

[[acceptance]]
text = "grimble-ci and grimble-arch share one verdict/finding type instead of CiFinding aliasing ArchFinding, with no layering violation"
bound = false

[[acceptance]]
text = "grimble check output for arch and ci findings is unchanged (existing tests pass)"
bound = false
+++

CiFinding aliases grimble_arch::ArchFinding; extract a shared type and wire grimble-ci (and grimble-arch) into grimble check. Also generate docs/reference/rules pages (gob-dev gen rules) once wired.
