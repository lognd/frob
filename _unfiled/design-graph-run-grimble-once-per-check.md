+++
id = "01M7EXR2BCZ1NXVE8TSP5D84WD"
title = "design graph: run grimble once per check"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:19:07Z"
updated = "2026-11-15T06:19:07Z"
labels = ["no-story"]
+++

Source: frob-audit2-repo.md M9/F14. Evidence: crates/frob-ledger/src/design.rs:227-257 launches grimble twice. Remedy: share the sibling result. Files: design.rs.
