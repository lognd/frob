+++
id = "01M4CTE5SS3BGF5R4PP5A9VYZQ"
title = "Snapshot content API: rules read the walked content, ban std::fs::read in rule code (audit M7)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:43Z"
updated = "2026-10-08T03:55:43Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/gob-rules/**", "crates/frob-check/**", "crates/grimble-check/**", "crates/crunk-check/**"]

[[acceptance]]
text = "Given rule crates, when the lint runs, then no rule body calls std::fs read functions (enforced by a rule or clippy disallowed_methods)"
bound = false
+++

notes/review/audit-2026-10-07.md M7: 15+ places read files from disk instead of the snapshot.
